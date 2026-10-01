# CineConIA · Safe ComfyUI installer

**3.0.0-rc.1 — PLAN V2 release candidate.** Stable 2.7.0 remains on `main`; this branch does not replace any published release.

[Download this test branch](https://github.com/chaLords/CineConIA-Installer/archive/refs/heads/feature/instalador-v2-seguro.zip) · [Español](README.md) · [Validation](docs/VALIDATION.md)

## Get started

1. Extract the ZIP on Windows x64. Allow 20 GB free at the destination, plus your models.
2. Run **ComfyUI-Setup.bat**. Language is detected automatically; Spanish and English are included.
3. Keep an existing installation unchanged or create an independent installation. Select a parent folder; a new `ComfyUI-CineConIA-V2` folder is created inside.
4. Setup verifies hardware, downloads a pinned official portable, prepares dependencies, installs essential nodes and tests the GPU and ComfyUI startup.
5. Use **ComfyUI - CineConIA V2**. Existing shortcuts are never replaced.

You do not need global Python, Git or CUDA Toolkit. Canceling the folder picker exits. Nonempty destinations are rejected.

## Recommended installation

- Embedded Python and PyTorch from ComfyUI v0.38.0; fixed archive hashes, no `latest` downloads.
- Existing Git or pinned, verified MinGit installed locally inside the portable. No global PATH changes.
- Visual C++ Runtime is installed through winget if missing; failure stops setup with instructions.
- Pinned ComfyUI-Manager classic, Cine con IA and VideoHelperSuite nodes.
- Official attention backend by default. Optional accelerators remain in advanced mode.
- PyTorch constraints protect the GPU backend from node dependencies.
- An actual FP16 GPU kernel, ComfyUI startup, node imports and dependency checks determine success.
- Model libraries may be linked in place, or copied/moved through the existing migration wizard with preview and confirmation. No models are automatically downloaded.

## Advanced mode

Run **ComfyUI-Advanced-Setup.bat** to select an existing installation manually, configure an existing portable with explicit authorization, choose accelerators and node groups, link multiple model libraries or select an output disk.

Existing manual/third-party installations are discovered and preserved. In-place configuration is restricted to portable layouts containing `python_embeded` and `ComfyUI`. Type `CONFIRMAR` to authorize dependency/node installation and launcher/configuration changes. Moving models requires separate confirmation.

## Hardware support

| Profile | Requirements |
|---|---|
| NVIDIA CUDA 13 | Compute capability ≥7.5, driver ≥580, Python 3.13 |
| NVIDIA CUDA 12.6 | Compute capability ≥5.0 and <10.0, driver ≥528.33, Python 3.12 |
| AMD / Intel | Corresponding official portable, followed by a real GPU operation |

Automatic selection respects GPU and driver compatibility. Unknown NVIDIA capability, old drivers and incompatible manual selections stop before downloading. Drivers are not installed or upgraded.

**Physically tested:** Windows 11, RTX 4060 Ti 16 GB, driver 616.92, Python 3.13.14 and PyTorch 2.14.0+cu130. AMD, Intel and older NVIDIA hardware remain release qualification candidates. Memory bus width and other unsupported telemetry are shown as unavailable, never guessed.

## Safety and recovery

Only empty, writable local fixed-disk destinations are accepted. System folders, overlapping installations and destination reparse points are rejected. Extraction uses a separate staging folder on the destination disk. Failed extraction preserves diagnostic files and never replaces a previous installation.

Discovery is bounded by time and depth; advanced manual selection covers locations outside that search. Model path configuration is backed up. Migration retains simulation, free-space checks, SHA-256 verification and explicit move confirmation.

Logs are stored in `logs/` beside setup and `_cineconia/instalacion-<timestamp>.log` inside the portable. `_cineconia/install-state.json` records base-ready/configuring/verified/needs-attention/interrupted states and detected versions. Rerun downloads to resume them. Use advanced mode and explicit consent to retry configuration of an existing portable. Full dependency rollback is not claimed; PyTorch recovery stops the installer if unsuccessful.

```text
ComfyUI-Setup.bat --diagnose
ComfyUI-Setup.bat --advanced
ComfyUI-Setup.bat --destination "D:\AI\ComfyUI-Test"
ComfyUI-Setup.bat --cuda 12.6
ComfyUI-Setup.bat --lang en
```

`--diagnose` inspects and saves a log only. `--no-shortcut` generates launchers without changing the desktop. **ComfyUI-Model-Migrator.bat** can use an existing portable's Python if global Python is unavailable.

## Development

Run `python -B -m unittest discover -s tests -v`. Bootstrap uses PowerShell 5.1; configuration and migration use Python. Compatibility, nodes and VRAM guidance live in `config/*.json`. Windows CI covers Python 3.12 and 3.13 and creates a test ZIP artifact without publishing a stable release.

[YouTube](https://www.youtube.com/@cineconia.oficial) · [Discord](https://discord.gg/hXKJ78cEua). Independent project, not affiliated with Comfy Org. See [LICENSE](LICENSE) and [third-party notices](assets/THIRD_PARTY_NOTICES.md).
