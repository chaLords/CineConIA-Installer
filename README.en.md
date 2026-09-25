<p align="center">
  <img src=".github/assets/logo-cineconia-comfyui.png" alt="Cine con IA · ComfyUI" width="320">
</p>

<h1 align="center">Clean ComfyUI Installation</h1>

<p align="center">
  <strong>Automatic, adaptive installer for Windows</strong><br>
  NVIDIA · AMD · Intel
</p>

<p align="center">
  <a href="README.md">Español</a> · <strong>English</strong>
</p>

<p align="center">
  Installs ComfyUI from scratch, detects the computer's hardware and automatically configures a suitable installation.
</p>

<p align="center">
  <a href="https://github.com/chaLords/CineConIA-Installer/releases/latest/download/CineConIA-Installer.zip"><img alt="Download the installer (.zip)" src="https://img.shields.io/badge/Download-installer%20.zip-2ea44f?style=for-the-badge"></a><br>
  <sub>Only what you need to install; the documentation stays here on GitHub.</sub>
</p>

<p align="center">
  <sub>No sponsors · No promotional shortcuts · No unnecessary software · No required models</sub><br>
  <sub>Made by <a href="https://www.youtube.com/@cineconia.oficial">Cine con IA</a> · Independent project, not affiliated with Comfy Org</sub>
</p>

---

## Automatic language selection

The installer and model migrator detect the language configured in Windows.

- Spanish Windows (display language or regional format) → Spanish.
- English or another Windows language → English.
- It asks nothing: it starts directly in the right language.
- If needed, force it with **--lang es** or **--lang en**.

Language-neutral entry files:

- **ComfyUI-Setup.bat** — installation.
- **ComfyUI-Model-Migrator.bat** — model migration.

Spanish compatibility aliases are also included:
**Instalar-ComfyUI.bat** and **Migrar-Modelos-ComfyUI.bat**. They run the same bilingual system.

## Which file should I run first?

For a new installation, the recommended order is:

1. **First: ComfyUI-Setup.bat**
   - Installs ComfyUI.
   - Detects the GPU and appropriate backend.
   - Configures compatible accelerators.
   - Offers the classic ComfyUI-Manager ("Manager" button).
   - Offers to install the Cine con IA custom nodes.
   - Offers to install the resource monitor (CPU, RAM, GPU, VRAM).
   - Looks for models from previous installations and offers to use them where they are
     or move them to a central library on another drive.
   - Creates launchers and a desktop shortcut named **ComfyUI**.

2. **Test ComfyUI once**
   - Open the **ComfyUI** desktop shortcut.
   - Make sure the interface starts correctly.
   - Close ComfyUI before migrating models.

3. **Only if you want to gather your models on another drive: ComfyUI-Model-Migrator.bat**
   - Finds or lets you select an existing model library.
   - Lets you choose another SSD/HDD for the models.
   - Shows a simulation first.
   - Can copy or safely move the files.
   - Can link the new library through extra_model_paths.yaml.

In short:

    ComfyUI-Setup.bat
            |
            v
       Test ComfyUI
            |
            v
       Close ComfyUI
            |
            v
    Gather models on another drive?
        /          \
      No            Yes
      |              |
      v              v
    Done    ComfyUI-Model-Migrator.bat

If you are starting from scratch and have no old models, you do not need to run the migrator.

If you already have ComfyUI and only want to reorganize or move its model library, you can run the model migrator independently.

## Quick start

1. Download **CineConIA-Installer.zip** with the button above and extract it into a
   simple folder such as **C:\ComfyUI**.
   Avoid OneDrive and paths with accents.
2. Run **ComfyUI-Setup.bat**.
3. Use the recommended automatic configuration, or choose Advanced mode.

When installation finishes there is a single desktop shortcut named **ComfyUI**.
The installer does not create promotional channel shortcuts or replace ComfyUI branding.

## How the adaptive installation works

### Before downloading

- Detects NVIDIA, AMD, or Intel.
- Modern NVIDIA cards (16/20 series or newer) use the official NVIDIA portable
  build (CUDA 13, Python 3.13).
- NVIDIA GPUs below compute capability 7.5 (GTX 10xx, GTX 9xx, TITAN V...) use the
  official nvidia_cu126 build (CUDA 12.6, Python 3.12).
- Modern card with a driver older than 580: the installer no longer falls back to
  CUDA 12.6 on its own. It recommends updating the driver (opens the NVIDIA page
  and closes the installer) and lets you install CUDA 13 anyway or CUDA 12.6.
- Before downloading it shows the recommended CUDA and gives you 10 seconds to
  change it with the **C** key. It has guards: CUDA 13 is never installed on cards
  older than the 16/20 series, and CUDA 12.6 is never installed on the 50 series,
  which only works with CUDA 13.
- You can also set it when running it: **ComfyUI-Setup.bat --cuda 12.6** or
  **--cuda 13**, with the same guards.
- AMD uses the official AMD/ROCm portable build.
- Intel uses the official Intel XPU portable build.
- Checks free space (15 GB), curl, and PowerShell.
- Warns when the folder is inside OneDrive or the path contains accents.

### Safer downloads

- Uses curl --fail so HTTP errors are not mistaken for successful downloads.
- Retries downloads.
- Downloads large files as .part first.
- If the download is interrupted, running the installer again resumes it.
- Compares the ComfyUI archive with the SHA-256 digest published by GitHub when available.
- Falls back to a 7-Zip integrity test if the release API does not provide a digest.
- Preserves an incomplete previous installation as a backup before reinstalling.
- Deletes the .7z archive after extraction to free ~2 GB.

### After ComfyUI is installed

The installer first checks for the Microsoft Visual C++ Redistributable (without it
PyTorch fails with a c10.dll error) and offers to install it with winget.

It then runs the embedded Python that belongs to the downloaded portable build and reads the environment that actually exists:

- Python.
- PyTorch.
- Real CUDA / ROCm-HIP / Intel XPU backend.
- GPU visible to PyTorch.
- VRAM.
- Compute capability when applicable.

If PyTorch cannot use the GPU (almost always an old driver), it warns before
continuing instead of leaving an installation that would only use the CPU.

Optional accelerators are then matched against that real environment instead of assuming a CUDA version.

## Accelerators

### Automatic configuration

On NVIDIA, SageAttention is attempted only when a wheel matches the actual PyTorch, CUDA, and Python combination, including wheels published for "this PyTorch version and higher". Triton is installed at the same version PyTorch itself declares on PyPI, and only when triton-windows has already published it. Because the portable's embedded Python lacks the include and libs folders Triton needs to compile, the installer adds them (triton-windows publishes them for each Python version).

AMD and Intel stay on their official portable backend and do not enter NVIDIA CUDA logic.

### Advanced mode

When compatible, advanced mode can offer:

- SageAttention.
- FlashAttention: searched in two sources (mjun0812 publishes for recent PyTorch versions; kingbri1 for older ones).
- Nunchaku: 4-bit **image** models (FLUX, Qwen-Image, Z-Image) for low-VRAM computers. Video does not need it. If your PyTorch is newer than the last one Nunchaku supports, the installer offers to switch to that version with the same CUDA; it saves the current state first (pip freeze in _cineconia\) and rolls back on its own if anything stops loading. It also installs the ComfyUI-nunchaku node.
- InsightFace / ONNX Runtime.

### PyTorch protection

Some nodes list a different PyTorch in their requirements and, once installed, leave ComfyUI without GPU or unable to start. The installer records the PyTorch version before each extra or node and, if anything changes it, restores the previous one and says so. If a requirement cannot be installed (for example because it needs compiling), the rest are installed one by one and the missing one is reported. At the end it runs pip check and shows any conflicts.

A successful pip install is not enough. SageAttention and FlashAttention are tested by running a real attention operation on the GPU; everything else is imported in a separate process. If the test fails, the component is not marked as operational and its launcher is not created.

Running the installer again re-verifies whatever already worked, so repeating the installation never downgrades the desktop shortcut.

## ComfyUI-Manager

The installer offers the **classic ComfyUI-Manager**, installed as a custom node in custom_nodes\comfyui-manager: the **"Manager"** button in the top bar, with "Install Missing Custom Nodes", "Model Manager", "Update All" and so on. It is the same interface almost every tutorial shows.

ComfyUI also ships an integrated Manager (--enable-manager, "Manage Extensions" button), but it has a different interface and, when enabled, disables the classic one. That is why the launchers do not use that flag. The integrated one is used only when Git is not available to install the classic one.

## Generated launchers

Launcher names follow the selected language. In English, examples include:

- Start-ComfyUI.bat
- Start-ComfyUI-Kitchen.bat
- Start-ComfyUI-SageAttention.bat
- Start-ComfyUI-FlashAttention.bat
- Start-ComfyUI-DynamicVRAM.bat on AMD
- Update-ComfyUI.bat
- Update-ComfyUI-and-Nodes.bat

Spanish installations use the equivalent Iniciar/Actualizar names.

Launchers check port 8188. If ComfyUI is already running, the existing interface is opened instead of launching a second instance.

The updaters move ComfyUI to the **latest stable release** (not the development branch). Update-ComfyUI-and-Nodes.bat saves a Manager snapshot first so you can roll back.

## Desktop shortcut

Only one desktop shortcut is created: **ComfyUI**.

It points to the best launcher that was actually verified:

1. SageAttention, if it works.
2. Comfy Kitchen, if available (NVIDIA only).
3. Base launcher as a fallback.

The shortcut uses the current ComfyUI logo (blue background, yellow "C"), shipped inside the installer as assets\ComfyUI.ico: it needs no download and is never replaced by channel branding.

## Git and custom nodes

Git is checked before cloning custom nodes. If Git is missing and winget is available, the installer asks whether Git for Windows should be installed.

It then offers to install:

- https://github.com/chaLords/ComfyUI-Cine-con-IA
- https://github.com/crystian/ComfyUI-Crystools — CPU, RAM, GPU, VRAM and temperature monitor in the ComfyUI top bar.
- Video nodes, with a single question: what MiniMax H3 and LTX workflows use.
  - https://github.com/kijai/ComfyUI-KJNodes
  - https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite
  - https://github.com/city96/ComfyUI-GGUF — GGUF models, the way to save VRAM for video.
  - https://github.com/facok/comfyui-SelfLift — progressive rendering for H3: first steps at low resolution, the rest at full resolution.

## Models

The installer does **not download models**.

It automatically searches your local drives for model folders from previous installations. Only if it finds one does it ask what to do:

1. **Use them where they are**: links them through extra_model_paths.yaml without copying or moving anything.
2. **Move them to a central library on another drive**: opens the same migrator as ComfyUI-Model-Migrator.bat (simulation, MIGRATE confirmation, SHA-256) and, when done, also links this ComfyUI to the new library.
3. **Do nothing.**

In later installations the central library is listed first and marked, so every future ComfyUI uses the same models on the drive you chose. It recognizes ComfyUI libraries as well as A1111 / Forge ones (Stable-diffusion, Lora, ESRGAN...).

The search covers every fixed local drive (not USB or network drives) and is bounded by depth, number of scanned folders, and number of results.

If extra_model_paths.yaml already exists, a .bak copy is made first and only the CineConIA-managed block is changed.

## Migrating models from an existing ComfyUI

Use **ComfyUI-Model-Migrator.bat** when you already have a large model collection.

Recommended flow:

1. Close ComfyUI.
2. Run the model migrator.
3. Let it search for old libraries or select them manually.
4. You can add multiple installations and consolidate them into one library.
5. Choose a parent folder on a large drive, for example:
   D:\AI\Models\ComfyUI
6. The resulting library is organized inside:
   D:\AI\Models\ComfyUI\models
7. Choose:
   - **Copy** — keeps all originals.
   - **Safe move** — on the same drive files are renamed (instant, no extra space);
     across drives each file is copied, verified with SHA-256, and only then is the original removed.
8. Review the **SIMULATION** before anything changes.
9. Type **MIGRATE** to confirm in English mode.
10. The migrator can update extra_model_paths.yaml for recognized ComfyUI installations.

### Model library structure

    models\
        checkpoints\
        diffusion_models\
        unet\
        text_encoders\
        clip\
        clip_vision\
        vae\
        loras\
        controlnet\
        upscale_models\
        embeddings\
        hypernetworks\
        style_models\
        gligen\
        latent_upscale_models\
        frame_interpolation\
        vae_approx\
        _sin_clasificar\

The internal folder _sin_clasificar remains language-independent so the same model library can be shared by Spanish and English installations. Files are placed there only when they cannot be classified safely from their existing folder structure. A1111 / Forge folders are translated to their equivalent (Stable-diffusion → checkpoints, Lora → loras, ESRGAN → upscale_models). The empty put_*_here placeholders from the portable build are ignored.

### Duplicates and conflicts

- Possible duplicates are confirmed with SHA-256.
- Same filename but different content is never overwritten; the conflict is preserved with a suffix such as __conflicto_2.
- In safe-move mode across drives, an original is removed only after the copied file is verified.
- If an error occurs, that original remains untouched.

### extra_model_paths.yaml

For recognized ComfyUI sources, the migrator can point the old installation to the new shared library.

If extra_model_paths.yaml already exists:

- a timestamped .bak backup is created first;
- only the CineConIA-managed block is added or replaced;
- unrelated configuration is preserved.

This allows several ComfyUI installations to share one 500 GB, 1 TB, or larger library on another drive.

### Migration report

Every confirmed migration stores a JSON report under:

    <library>\_cineconia_migracion\

It records sources, destination, migration mode, duplicates, conflicts, errors, and updated extra_model_paths.yaml files.

## Compatibility philosophy

Compatible → install and verify.
Uncertain → skip.
Not compatible → use a fallback.

An optional optimization should never break a working base installation.

## License

The installer is MIT. ComfyUI and external components keep their own licenses. See [assets/THIRD_PARTY_NOTICES.md](assets/THIRD_PARTY_NOTICES.md).
