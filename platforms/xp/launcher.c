/* XP-compatible launcher. Only kernel32/user32 APIs; no C runtime dependency. */
#define WIN32_LEAN_AND_MEAN
#define _WIN32_WINNT 0x0501
#include <windows.h>

static WCHAR base[32768], interpreter[32768], command[32768];
static STARTUPINFOW startup;
static PROCESS_INFORMATION process;

static BOOL append(WCHAR *target, DWORD *used, LPCWSTR text) {
    while (*text) {
        if (*used >= 32766) return FALSE;
        target[(*used)++] = *text++;
    }
    target[*used] = 0;
    return TRUE;
}

void WinMainCRTStartup(void) {
    DWORD size, i, used = 0, code = 1;
    LPWSTR arguments = GetCommandLineW();
    /* Old bundled OpenSSL SHAEXT code is broken on newer x64 CPUs.
       Use the documented scalar dispatch for this process and its child only.
       Certificate checks and cryptographic algorithms remain enabled. */
    if (!SetEnvironmentVariableW(L"OPENSSL_ia32cap", L":~0x20000000")) goto failed;
    size = GetModuleFileNameW(NULL, base, 32768);
    if (!size || size >= 32768) goto failed;
    for (i = size; i > 0; --i) {
        if (base[i-1] == L'\\' || base[i-1] == L'/') { base[i-1] = 0; break; }
    }
    if (!i) goto failed;
    if (*arguments == L'"') { ++arguments; while (*arguments && *arguments != L'"') ++arguments; if (*arguments) ++arguments; }
    else { while (*arguments && *arguments != L' ' && *arguments != L'\t') ++arguments; }
    while (*arguments == L' ' || *arguments == L'\t') ++arguments;
    if (!append(interpreter, &used, base) || !append(interpreter, &used, L"\\runtime\\pythonw.exe")) goto failed;
    used = 0;
    if (!append(command, &used, L"\"") || !append(command, &used, interpreter) ||
        !append(command, &used, L"\" -I \"") || !append(command, &used, base) ||
        !append(command, &used, L"\\run_xp.py\" ") || !append(command, &used, arguments)) goto failed;
    startup.cb = sizeof(startup);
    if (!CreateProcessW(interpreter, command, NULL, NULL, FALSE, CREATE_NO_WINDOW,
                        NULL, base, &startup, &process)) goto failed;
    CloseHandle(process.hThread);
    WaitForSingleObject(process.hProcess, INFINITE);
    if (!GetExitCodeProcess(process.hProcess, &code)) code = 1;
    CloseHandle(process.hProcess);
    ExitProcess(code);
failed:
    MessageBoxW(NULL, L"DX Talker could not start its bundled XP runtime. Reinstall the matching 32 bit or 64 bit package.", L"DX Talker", MB_OK | MB_ICONERROR);
    ExitProcess(1);
}
