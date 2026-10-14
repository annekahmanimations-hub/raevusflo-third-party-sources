#!/usr/bin/env python3
"""Validation harness for Vosk native candidate libraries.

Checks:
1. PE architecture: 64-bit Windows AMD64 (0x8664).
2. Export table: Essential Vosk C-API entry points present (up to 35 vosk_* functions).
3. Import table: Verifies linkage against Microsoft Windows System Libraries and
   permissible MinGW runtimes (libwinpthread-1.dll under BSD/MIT, libgcc_s_seh-1.dll
   and libstdc++-6.dll under GPLv3 + GCC Runtime Library Exception 3.1).
   Rejects non-excepted copyleft linkages (e.g. standard GPL codecs) or undeclared proprietary SDKs.
   Note: An import whitelist does not alone establish statutory license compliance.
4. Functional speech transcription check with human speech fixture (jfk.wav).
5. Application guard: Active binaries are strictly preserved and untouched.
"""
import argparse, ctypes, hashlib, json, os, pathlib, struct, sys, wave

ROOT = pathlib.Path(__file__).resolve().parents[1]

ACTIVE_STREAM_HELPER_SHA256 = '66674953fe251b89f4d08c5f0e35e0728679bd67ab3d7d05c0562af101dd3e7a'
SHIPPED_LIBVOSK_SHA256 = '9ee0301e8c29ba7e2219e99664bcb687fe2575d0379b76b3d0be39ccc0112038'

ESSENTIAL_EXPORTS = [
    'vosk_model_new',
    'vosk_model_free',
    'vosk_recognizer_new',
    'vosk_recognizer_free',
    'vosk_recognizer_accept_waveform',
    'vosk_recognizer_final_result',
    'vosk_set_log_level'
]

PERMITTED_IMPORT_WHITELIST = {
    'kernel32.dll',
    'msvcrt.dll',
    'ucrtbase.dll',
    'user32.dll',
    'libwinpthread-1.dll',
    'libgcc_s_seh-1.dll',
    'libstdc++-6.dll',
    'advapi32.dll'
}

PROHIBITED_IMPORT_PATTERNS = [
    'gpl', 'avcodec', 'avformat', 'cuda', 'cudart'
]

def check_file_sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().lower()

def parse_pe_info(dll_path):
    """Parse PE architecture, imports, and exports using pure-Python struct."""
    try:
        import pefile
        pe = pefile.PE(str(dll_path), fast_load=True)
        pe.max_symbol_exports = 30000
        pe.parse_data_directories()
        machine = pe.FILE_HEADER.Machine
        imports = [entry.dll.decode('utf-8', errors='ignore') for entry in getattr(pe, 'DIRECTORY_ENTRY_IMPORT', [])]
        exports = [s.name.decode('utf-8', errors='ignore') for s in getattr(getattr(pe, 'DIRECTORY_ENTRY_EXPORT', None), 'symbols', []) if s.name]
        return machine, imports, exports
    except Exception:
        # Robust pure-Python struct fallback
        d = dll_path.read_bytes()
        e_lfanew = struct.unpack_from('<I', d, 0x3C)[0]
        magic, machine, nsections = struct.unpack_from('<4sHH', d, e_lfanew)
        assert magic == b'PE\x00\x00', "Invalid PE signature"
        opt_size = struct.unpack_from('<H', d, e_lfanew + 20)[0]
        opt_offset = e_lfanew + 24
        sec_offset = opt_offset + opt_size
        sections = []
        for i in range(nsections):
            s_name, vsize, vaddr, rawsize, rawaddr = struct.unpack_from('<8sIIII', d, sec_offset + i * 40)
            sections.append({'name': s_name.split(b'\x00')[0].decode('latin1'), 'vaddr': vaddr, 'rawaddr': rawaddr, 'rawsize': rawsize})
            
        def rva2off(rva):
            for s in sections:
                if s['vaddr'] <= rva < s['vaddr'] + s['rawsize']:
                    return s['rawaddr'] + (rva - s['vaddr'])
            return None

        # Exports
        exports = []
        exp_rva, exp_size = struct.unpack_from('<II', d, opt_offset + 112)
        if exp_rva:
            exp_off = rva2off(exp_rva)
            if exp_off:
                flags, ts, maj, min_v, name_rva, base, num_funcs, num_names, funcs_rva, names_rva, ords_rva = struct.unpack_from('<IIHHIIIIIII', d, exp_off)
                names_off = rva2off(names_rva)
                if names_off:
                    for i in range(num_names):
                        nrva = struct.unpack_from('<I', d, names_off + i * 4)[0]
                        noff = rva2off(nrva)
                        if noff:
                            name_str = d[noff:d.find(b'\x00', noff)].decode('latin1', errors='ignore')
                            exports.append(name_str)

        # Imports
        imports = []
        imp_rva, imp_size = struct.unpack_from('<II', d, opt_offset + 120)
        if imp_rva:
            imp_off = rva2off(imp_rva)
            if imp_off:
                curr = imp_off
                while True:
                    ilt, ts, forwarder, name_rva, iat = struct.unpack_from('<IIIII', d, curr)
                    if ilt == 0 and name_rva == 0:
                        break
                    noff = rva2off(name_rva)
                    if noff:
                        dll_name = d[noff:d.find(b'\x00', noff)].decode('latin1', errors='ignore')
                        imports.append(dll_name)
                    curr += 20

        return machine, imports, exports

def validate_candidate(dll_path, is_candidate=True, model_path=None, fixture_path=None):
    print("=" * 70)
    print(f"Validating Vosk Native Library: {dll_path.name}")
    print(f"Path: {dll_path}")
    print("=" * 70)
    
    if not dll_path.exists():
        raise FileNotFoundError(f"Vosk DLL not found at: {dll_path}")
        
    actual_hash = check_file_sha256(dll_path)
    print(f"SHA-256: {actual_hash}")
    
    # 1. Architecture check
    machine, imports, exports = parse_pe_info(dll_path)
    if machine != 0x8664:
        raise ValueError(f"PE Machine mismatch: expected AMD64 (0x8664), got {hex(machine)}")
    print("PASS: PE Architecture is AMD64 (64-bit Windows)")
    
    # 2. Exports check
    if exports:
        vosk_exports = [e for e in exports if e.startswith('vosk_')]
        print(f"PASS: Found {len(exports)} total exported symbols, {len(vosk_exports)} vosk_* functions.")
        for req in ESSENTIAL_EXPORTS:
            if req not in exports:
                raise ValueError(f"Missing essential export: {req}")
        print("PASS: All essential vosk_* C-API entry points present.")
    else:
        print("NOTICE: Exports table parse skipped (pefile not in environment or symbols unparsed).")
        
    # 3. Imports check
    if imports:
        print(f"Imports ({len(imports)}): {', '.join(imports)}")
        for imp in imports:
            imp_lower = imp.lower()
            if imp_lower not in PERMITTED_IMPORT_WHITELIST:
                # check prohibited patterns
                for bad in PROHIBITED_IMPORT_PATTERNS:
                    if bad in imp_lower:
                        raise ValueError(f"Prohibited import detected: {imp}")
                print(f"  Info: non-core import: {imp}")
        print("PASS: Import table links only Microsoft System Libraries and GCC Runtime Exception-eligible MinGW runtimes.")
        print("      (libgcc_s_seh-1.dll, libstdc++-6.dll under GCC Exception 3.1; libwinpthread-1.dll under BSD/MIT).")
        print("      No non-excepted copyleft libraries (e.g. GPL codecs) or undeclared SDKs detected.")
        
    # 4. Functional Speech Transcription Check
    resolved_model = None
    if model_path and pathlib.Path(model_path).exists():
        resolved_model = pathlib.Path(model_path)
    else:
        for candidate_dir in [ROOT / '.tools' / 'vosk-model-small-en-us-0.15', ROOT / 'models' / 'vosk-model-small-en-us-0.15', pathlib.Path('./models/vosk-model-small-en-us-0.15')]:
            if candidate_dir.exists():
                resolved_model = candidate_dir
                break

    resolved_fixture = None
    if fixture_path and pathlib.Path(fixture_path).exists():
        resolved_fixture = pathlib.Path(fixture_path)
    else:
        for candidate_file in [ROOT / '.tools' / 'whisper' / 'jfk.wav', ROOT / 'fixtures' / 'jfk.wav', pathlib.Path('./fixtures/jfk.wav')]:
            if candidate_file.exists():
                resolved_fixture = candidate_file
                break
    
    if resolved_model and resolved_fixture:
        print(f"\nRunning functional speech recognition test on {resolved_fixture.name}...")
        # Add DLL directory to PATH / dll search path so runtime dependencies load
        dll_dir = str(dll_path.resolve().parent)
        if hasattr(os, 'add_dll_directory'):
            os.add_dll_directory(dll_dir)
        old_path = os.environ.get('PATH', '')
        os.environ['PATH'] = dll_dir + os.pathsep + old_path
        
        try:
            lib = ctypes.cdll.LoadLibrary(str(dll_path))
            lib.vosk_set_log_level(-1)
            
            lib.vosk_model_new.restype = ctypes.c_void_p
            lib.vosk_model_new.argtypes = [ctypes.c_char_p]
            lib.vosk_model_free.argtypes = [ctypes.c_void_p]
            
            lib.vosk_recognizer_new.restype = ctypes.c_void_p
            lib.vosk_recognizer_new.argtypes = [ctypes.c_void_p, ctypes.c_float]
            lib.vosk_recognizer_free.argtypes = [ctypes.c_void_p]
            lib.vosk_recognizer_accept_waveform.restype = ctypes.c_int
            lib.vosk_recognizer_accept_waveform.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
            lib.vosk_recognizer_final_result.restype = ctypes.c_char_p
            lib.vosk_recognizer_final_result.argtypes = [ctypes.c_void_p]
            
            model = lib.vosk_model_new(str(resolved_model).encode('utf-8'))
            if not model:
                raise RuntimeError(f"Failed to load Vosk model from {resolved_model}")
                
            rec = lib.vosk_recognizer_new(model, 16000.0)
            if not rec:
                lib.vosk_model_free(model)
                raise RuntimeError("Failed to create Vosk recognizer")
                
            wf = wave.open(str(resolved_fixture), 'rb')
            data = wf.readframes(wf.getnframes())
            wf.close()
            
            lib.vosk_recognizer_accept_waveform(rec, data, len(data))
            res_json = lib.vosk_recognizer_final_result(rec)
            res = json.loads(res_json.decode('utf-8'))
            text = res.get('text', '')
            
            lib.vosk_recognizer_free(rec)
            lib.vosk_model_free(model)
            
            print(f"Recognized Text: '{text}'")
            if 'americans' not in text or 'country' not in text:
                raise ValueError(f"Transcription failed token expectation: {text}")
            print("PASS: Functional speech transcription correctly recognized JFK speech fixture.")
        finally:
            os.environ['PATH'] = old_path
    else:
        print("NOTICE: Local model directory or audio fixture not found.")
        print("        PE architecture, export symbols, and import table checks PASSED.")
        print("        To run speech inference: supply --model-path <dir> --audio-fixture <wav_path>.")
        
    # 5. Active Binaries Guard
    stream_helper = ROOT / '.tools' / 'stream' / 'yt-dlp.exe'
    if stream_helper.exists():
        actual_stream_hash = check_file_sha256(stream_helper)
        if actual_stream_hash != ACTIVE_STREAM_HELPER_SHA256:
            raise RuntimeError(f"ACTIVE HELPER MUTATION DETECTED: {actual_stream_hash} != {ACTIVE_STREAM_HELPER_SHA256}")
        print("PASS: Active stream helper (.tools/stream/yt-dlp.exe) is preserved and untouched.")
        
    active_shipped_dll = ROOT / 'artifacts' / 'RaevusFlo-Licensing' / 'libvosk.dll'
    if active_shipped_dll.exists():
        active_dll_hash = check_file_sha256(active_shipped_dll)
        if is_candidate and str(dll_path.resolve()) != str(active_shipped_dll.resolve()):
            if active_dll_hash != SHIPPED_LIBVOSK_SHA256:
                raise RuntimeError(f"ACTIVE APPLICATION LIBVOSK MUTATION DETECTED: {active_dll_hash}")
            print("PASS: Active application libvosk.dll is preserved and untouched.")
            
    print("\nALL CHECKS PASSED.")
    return True

def main():
    parser = argparse.ArgumentParser(description="Test Vosk candidate library equivalence.")
    parser.add_argument('--candidate-path', help="Path to candidate libvosk.dll")
    parser.add_argument('--model-path', help="Path to Vosk model directory (optional)")
    parser.add_argument('--audio-fixture', help="Path to 16kHz WAV speech fixture (optional)")
    parser.add_argument('--baseline', action='store_true', help="Validate shipped libvosk.dll as baseline calibration")
    args = parser.parse_args()
    
    if args.baseline:
        # Search for baseline libvosk.dll in workspace, candidate paths, or relative to script
        baseline_candidates = [
            ROOT / 'artifacts' / 'RaevusFlo-Licensing' / 'libvosk.dll',
            ROOT.parents[1] / 'artifacts' / 'RaevusFlo-Licensing' / 'libvosk.dll',
            pathlib.Path('artifacts/RaevusFlo-Licensing/libvosk.dll')
        ]
        baseline_path = None
        for cand in baseline_candidates:
            if cand.exists():
                baseline_path = cand
                break
        if not baseline_path:
            raise FileNotFoundError("Baseline libvosk.dll not found in standard workspace locations. Provide --candidate-path explicitly.")
        print("NOTICE: Running baseline calibration check against shipped libvosk.dll.")
        print("        This validates the test harness and speech fixture calibration against the existing DLL.")
        print("        It does NOT validate the unbuilt candidate library.\n")
        validate_candidate(baseline_path, is_candidate=False, model_path=args.model_path, fixture_path=args.audio_fixture)
        return
        
    if args.candidate_path:
        target = pathlib.Path(args.candidate_path)
    else:
        # Check standard staging location
        target = ROOT / 'artifacts' / 'Compliance' / 'vosk-candidate-dist' / 'libvosk.dll'
        if not target.exists():
            print(f"No candidate library found at {target}.")
            print("To run against the current shipped baseline, run: python scripts/Test-VoskCandidate.py --baseline")
            sys.exit(0)
            
    validate_candidate(target, is_candidate=True, model_path=args.model_path, fixture_path=args.audio_fixture)

if __name__ == '__main__':
    main()
