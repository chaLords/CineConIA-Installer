<p align="center">
  <a href="README.md">🇪🇸 Español</a> · <strong>🇬🇧 English</strong>
</p>

<h1 align="center">Cine con IA Installer</h1>

<p align="center">
  <strong>Adaptive ComfyUI installation based on your real hardware.</strong><br>
  NVIDIA · AMD · Intel · No model downloads · No third-party branding
</p>

<p align="center">
  <a href="LICENSE"><img alt="MIT License" src="https://img.shields.io/badge/license-MIT-blue?style=flat-square"></a>
  <img alt="Windows" src="https://img.shields.io/badge/Windows-10%20%2F%2011-0078d4?style=flat-square&logo=windows&logoColor=white">
  <img alt="Adaptive branch" src="https://img.shields.io/badge/branch-v2--adaptive--installer-7c3aed?style=flat-square">
  <a href="https://www.youtube.com/@cineconia.oficial"><img alt="YouTube channel" src="https://img.shields.io/badge/youtube-Cine%20con%20IA-red?style=flat-square&logo=youtube&logoColor=white"></a>
</p>

<p align="center">
  Detects the computer, installs the appropriate portable build, verifies optional accelerators, and creates a clean desktop shortcut named <strong>ComfyUI</strong>.
</p>

---

## Automatic language selection

The installer and model migrator detect the language configured in Windows.

- Spanish Windows → Spanish.
- English or another Windows language → English by default.
- At startup you can switch manually between Spanish and English.
- You can also force a language with **--lang=es** or **--lang=en**.

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
   - Offers to install the Cine con IA custom nodes.
   - Creates launchers and a desktop shortcut named **ComfyUI**.

2. **Test ComfyUI once**
   - Open the **ComfyUI** desktop shortcut.
   - Make sure the interface starts correctly.
   - Close ComfyUI before migrating models.

3. **Only if you already have old models: ComfyUI-Model-Migrator.bat**
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
    Already have models?
        /          \
      No            Yes
      |              |
      v              v
    Done    ComfyUI-Model-Migrator.bat

If you are starting from scratch and have no old models, you do not need to run the migrator.

If you already have ComfyUI and only want to reorganize or move its model library, you can run the model migrator independently.

## Quick start

1. Download or extract the repository.
2. Run **ComfyUI-Setup.bat**.
3. Use the recommended automatic configuration, or choose Advanced mode.

When installation finishes there is a single desktop shortcut named **ComfyUI**.
The installer does not create promotional channel shortcuts or replace ComfyUI branding.

## How the adaptive installation works

### Before downloading

- Detects NVIDIA, AMD, or Intel.
- Modern NVIDIA systems use the current official NVIDIA portable build.
- Older NVIDIA hardware/drivers can use the official nvidia_cu126 fallback.
- AMD uses the official AMD/ROCm portable build.
- Intel uses the official Intel XPU portable build.
- Checks free space, curl, and PowerShell.

### Safer downloads

- Uses curl --fail so HTTP errors are not mistaken for successful downloads.
- Retries downloads.
- Downloads large files as .part first.
- Compares the ComfyUI archive with the SHA-256 digest published by GitHub when available.
- Falls back to a 7-Zip integrity test if the release API does not provide a digest.
- Preserves an incomplete previous installation as a backup before reinstalling.

### After ComfyUI is installed

The installer runs the embedded Python that belongs to the downloaded portable build and reads the environment that actually exists:

- Python.
- PyTorch.
- Real CUDA / ROCm-HIP / Intel XPU backend.
- GPU visible to PyTorch.
- VRAM.
- Compute capability when applicable.

Optional accelerators are then matched against that real environment instead of assuming a CUDA version.

## Accelerators

### Automatic configuration

On NVIDIA, SageAttention is attempted only when a wheel matches the actual PyTorch, CUDA, and Python combination. Triton is installed only when there is a known safe rule for that PyTorch branch.

AMD and Intel stay on their official portable backend and do not enter NVIDIA CUDA logic.

### Advanced mode

When compatible, advanced mode can offer:

- SageAttention.
- FlashAttention.
- Nunchaku.
- InsightFace / ONNX Runtime.

A successful pip install is not enough. The module is imported in a separate process. If the import fails, the component is not marked as operational and its launcher is not created.

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

## Desktop shortcut

Only one desktop shortcut is created: **ComfyUI**.

It points to the best launcher that was actually verified:

1. SageAttention, if it works.
2. Comfy Kitchen, if available.
3. Base launcher as a fallback.

The installer attempts to use the ComfyUI favicon from the official Comfy-Org documentation repository. If it cannot obtain it, it does not substitute channel branding.

## Git and custom nodes

Git is checked before cloning custom nodes. If Git is missing and winget is available, the installer asks whether Git for Windows should be installed.

It then offers to install:

    https://github.com/chaLords/ComfyUI-Cine-con-IA

## Models

The installer does **not download models**.

It can optionally find another ComfyUI model library and create extra_model_paths.yaml so existing models can be reused without copying them.

The search is bounded by depth, number of scanned folders, and number of results.

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
   - **Safe move** — copies each file, verifies SHA-256, then removes the original.
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

The internal folder _sin_clasificar remains language-independent so the same model library can be shared by Spanish and English installations. Files are placed there only when they cannot be classified safely from their existing folder structure.

### Duplicates and conflicts

- Possible duplicates are confirmed with SHA-256.
- Same filename but different content is never overwritten; the conflict is preserved with a suffix such as __conflicto_2.
- In safe-move mode an original is removed only after the copied file is verified.
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

The installer is MIT. ComfyUI and external components keep their own licenses. See THIRD_PARTY_NOTICES.md.
