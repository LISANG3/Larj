# Everything SDK Runtime Directory

Larj uses the official Everything SDK DLL for deep integration.

## Download

Download:
https://www.voidtools.com/downloads/

## Installation

1. Download Everything SDK from:
   https://www.voidtools.com/Everything-SDK.zip
2. For x64 Python, place `Everything64.dll` in this directory.
3. For x86 Python, place `Everything32.dll` in this directory.
4. (Optional) Place `Everything.exe` in this directory for auto `-start-service`.

## Usage

Larj loads SDK DLL directly and queries through official IPC APIs.

If auto start is enabled, Larj may run:

`Everything.exe -start-service`

## Note

`Everything64.dll` / `Everything32.dll` / `Everything.exe` are not included in the repository due to licensing.
Please download them from the official Everything website.
