"""Regression tests for the safety boundary before downloads and mutations."""
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import configuracion as config
import instalador as ins
import lanzadores
import verificacion
import modelos_enlace


class PolicyTests(unittest.TestCase):
    def test_recommended_catalog_is_small_and_pinned(self):
        nodes=config.nodos()
        self.assertEqual({k for k,v in nodes.items() if v['recommended']},{'manager','cineconia','vhs'})
        self.assertTrue(all(len(n['version'])==40 for n in nodes.values()))

    def test_vram_rounding_and_unknown(self):
        self.assertIsNone(config.perfil_vram(None))
        self.assertEqual(config.perfil_vram(15.9)['name'],'16 GB')
        self.assertEqual(config.perfil_vram(4)['name'],'<8 GB')
        self.assertEqual(config.perfil_vram(96)['name'],'64 GB+')

    def test_direct_invocation_requires_explicit_consent(self):
        with patch.dict(os.environ,{},clear=True),contextlib.redirect_stdout(io.StringIO()):
            self.assertFalse(config.autorizar('C:/old',lambda _:''))
            self.assertFalse(config.autorizar('C:/old',lambda _:'yes'))
            self.assertTrue(config.autorizar('C:/old',lambda _:'CONFIRMAR'))

    def test_authorization_is_bound_to_destination(self):
        with patch.dict(os.environ,{'CIA_AUTHORIZED_DESTINATION':'C:/new'}),contextlib.redirect_stdout(io.StringIO()):
            self.assertFalse(config.autorizar('C:/old',lambda _:''))
            self.assertTrue(config.autorizar('C:/new',lambda _:self.fail('unexpected prompt')))

    def test_gpu_unavailable_always_stops(self):
        with patch.object(ins,'preguntar',side_effect=AssertionError('no bypass')),contextlib.redirect_stdout(io.StringIO()):
            self.assertFalse(ins.gpu_utilizable({'gpu_inutilizable':True,'fabricante':'nvidia'}))

    def test_state_preserves_selected_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            config.guardar_estado(folder,status='base_ready',output_directory='D:/outputs')
            config.guardar_estado(folder,status='verified')
            self.assertEqual(config.leer_estado(folder)['output_directory'],'D:/outputs')
            self.assertEqual(config.leer_estado(folder)['status'],'verified')

    def test_runtime_mismatch_stops_before_nodes(self):
        with patch.dict(os.environ,{'CIA_PROFILE':'nvidia','CIA_OPERATION':'new'}):
            with self.assertRaisesRegex(RuntimeError,'PYTHON_MATRIX_MISMATCH'):
                config.validar_entorno('.',{'python':'3.12.10'})

    def test_recommended_nodes_do_not_prompt(self):
        with patch.dict(os.environ,{'CINECONIA_MODE':'recommended'}),patch.object(ins,'ruta_nodo',return_value=None),patch.object(ins.preflight,'git_exe',return_value='git'),patch.object(ins,'preguntar',side_effect=AssertionError('prompt')),patch.object(ins,'clonar_nodo',return_value=True) as clone,contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(ins.instalar_nodo('new','python','cineconia'))
            self.assertFalse(ins.instalar_nodo('new','python','monitor'))
            clone.assert_called_once_with('new','python','cineconia',None)

    def test_recommended_video_only_installs_vhs(self):
        ins.ESTADOS_NODOS.clear()
        with patch.dict(os.environ,{'CINECONIA_MODE':'recommended'}),patch.object(ins,'ruta_nodo',return_value=None),patch.object(ins.preflight,'git_exe',return_value='git'),patch.object(ins,'preguntar',side_effect=AssertionError('prompt')),patch.object(ins,'clonar_nodo',return_value=True) as clone,contextlib.redirect_stdout(io.StringIO()):
            _,accepted=ins.instalar_grupo('new','python','video')
            self.assertTrue(accepted)
            clone.assert_called_once_with('new','python','vhs',None)

    def test_gpu_kernel_failure_not_success(self):
        with patch.object(verificacion.subprocess,'run',return_value=subprocess.CompletedProcess([],1,'','no kernel image')):
            ok,detail=verificacion.comprobar_gpu('python','nvidia')
            self.assertFalse(ok)
            self.assertIn('no kernel',detail)

    def test_desktop_shortcut_avoids_overwriting(self):
        with patch.object(lanzadores,'_copiar_icono',return_value=None),patch.object(lanzadores.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'','')) as run:
            lanzadores.crear_acceso_escritorio('C:/new','C:/new/start.bat')
        script=run.call_args.args[0][-1]
        self.assertIn('while(Test-Path -LiteralPath $p)',script)
        self.assertNotIn("Join-Path $d 'ComfyUI.lnk'",script)

    def test_locale_keys_match_and_placeholders_parse(self):
        es=json.loads((ROOT/'src/locales/es.json').read_text(encoding='utf-8'))
        en=json.loads((ROOT/'src/locales/en.json').read_text(encoding='utf-8'))
        self.assertEqual(set(es),set(en))

    def test_multiple_libraries_preserve_custom_yaml_and_sources(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder)
            comfy=base/'ComfyUI'; comfy.mkdir()
            yaml=comfy/'extra_model_paths.yaml'
            yaml.write_text('user_library:\n    base_path: D:/other\n')
            sources=[]
            for name in ('library-a','library-b'):
                models=base/name
                (models/'checkpoints').mkdir(parents=True)
                (models/'checkpoints/model.bin').write_bytes(b'preserve')
                sources.append(str(models))
            _,backup=modelos_enlace.actualizar_yaml(str(comfy),sources[0],bibliotecas=sources)
            content=yaml.read_text(encoding='utf-8')
            self.assertIn('user_library:',content)
            self.assertIn('cineconia_model_library_1:',content)
            self.assertIn('cineconia_model_library_2:',content)
            self.assertTrue(Path(backup).exists())
            for models in sources:
                self.assertEqual(Path(models,'checkpoints/model.bin').read_bytes(),b'preserve')
            modelos_enlace.actualizar_yaml(str(comfy),sources[0],bibliotecas=sources)
            self.assertEqual(content,yaml.read_text(encoding='utf-8'))

    def test_checkout_failure_preserves_incomplete_user_node(self):
        with tempfile.TemporaryDirectory() as folder,contextlib.redirect_stdout(io.StringIO()):
            old=Path(folder,'ComfyUI/custom_nodes/ComfyUI-Cine-con-IA')
            old.mkdir(parents=True); (old/'user.txt').write_text('preserve')
            def run(cmd,*args,**kwargs):
                if cmd[1]=='clone':
                    Path(cmd[-1],'__init__.py').write_text('')
                    return True,[]
                return False,['pinned revision unavailable']
            with patch.object(ins.preflight,'git_exe',return_value='git'),patch.object(ins.pasos,'correr',side_effect=run):
                self.assertFalse(ins.clonar_nodo(folder,'python','cineconia'))
            self.assertEqual((old/'user.txt').read_text(),'preserve')


PS=shutil.which('powershell.exe')


@unittest.skipUnless(PS,'Windows PowerShell required')
class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder=Path(self.tmp.name)

    def ps(self,code):
        lib=str(ROOT/'src/bootstrap.ps1').replace("'","''")
        script=f"$ErrorActionPreference='Stop'; . '{lib}' -LibraryOnly; try {{ {code} }} catch {{ Write-Output $_.Exception.Message; exit 1 }}"
        return subprocess.run([PS,'-NoProfile','-ExecutionPolicy','Bypass','-Command',script],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=45)

    def quote(self,path):
        return "'"+str(path).replace("'","''")+"'"

    def test_parser_windows_powershell_51(self):
        (ROOT/'src/bootstrap.ps1').read_bytes().decode('ascii')
        r=self.ps("'loaded'")
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)

    def test_destination_does_not_touch_existing_files(self):
        marker=self.folder/'user-model.bin'
        marker.write_bytes(b'keep')
        r=self.ps(f'Assert-Destination {self.quote(self.folder)} @() 0')
        self.assertNotEqual(r.returncode,0)
        self.assertIn('PATH_NOT_EMPTY',r.stdout)
        self.assertEqual(marker.read_bytes(),b'keep')

    def test_destination_sibling_not_false_positive(self):
        old=self.folder/'ComfyUI'; old.mkdir()
        new=self.folder/'ComfyUI-new'
        r=self.ps(f'Assert-Destination {self.quote(new)} @([pscustomobject]@{{root={self.quote(old)}}}) 0')
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)

    def test_destination_rejects_nested_installation(self):
        old=self.folder/'ComfyUI'; old.mkdir()
        r=self.ps(f'Assert-Destination {self.quote(old/"new")} @([pscustomobject]@{{root={self.quote(old)}}}) 0')
        self.assertNotEqual(r.returncode,0)
        self.assertIn('PATH_OVERLAP',r.stdout)

    def test_low_space_blocks_before_creating_destination(self):
        new=self.folder/'new'
        r=self.ps(f'Assert-Destination {self.quote(new)} @() 99999999')
        self.assertNotEqual(r.returncode,0)
        self.assertIn('DISK_SPACE',r.stdout)
        self.assertFalse(new.exists())

    def test_unsafe_cmd_path_rejected(self):
        r=self.ps(f'Assert-Destination {self.quote(self.folder/"percent%PATH%")} @() 0')
        self.assertIn('PATH_UNSAFE_CHARACTERS',r.stdout)

    def test_drive_relative_path_rejected(self):
        self.assertIn('PATH_LOCAL_ABSOLUTE_REQUIRED',self.ps("Assert-Destination 'C:relative' @() 0").stdout)

    def test_destination_changed_during_extraction_is_preserved(self):
        old=self.folder/'old'; old.mkdir()
        code=r'''
function powershell.exe {
    $stage=$args[([Array]::IndexOf($args,'-Destino')+1)]
    [IO.Directory]::CreateDirectory((Join-Path $stage 'portable/python_embeded')) | Out-Null
    [IO.Directory]::CreateDirectory((Join-Path $stage 'portable/ComfyUI')) | Out-Null
    [IO.File]::WriteAllText((Join-Path $stage 'portable/python_embeded/python.exe'),'')
    [IO.File]::WriteAllText((Join-Path $stage 'portable/ComfyUI/main.py'),'')
    [IO.File]::WriteAllText((Join-Path $target 'user.txt'),'data')
    $global:LASTEXITCODE=0
}
Expand-Portable 'unused.7z' 'unused.exe' $target
'''
        r=self.ps(f'$target={self.quote(old)};'+code)
        self.assertNotEqual(r.returncode,0)
        self.assertIn('DESTINATION_CHANGED_DURING_DOWNLOAD',r.stdout)
        self.assertEqual((old/'user.txt').read_text(),'data')

    def test_wrong_download_hash_is_quarantined(self):
        target=self.folder/'download.exe'
        code=r'''
function powershell.exe {
    $partial=$args[([Array]::IndexOf($args,'-Salida')+1)]
    [IO.File]::WriteAllText($partial,'corrupt')
    $global:LASTEXITCODE=0
}
Get-VerifiedDownload ([pscustomobject]@{url='https://example.invalid/file';sha256=('0'*64)}) $target
'''
        r=self.ps(f'$target={self.quote(target)};'+code)
        self.assertNotEqual(r.returncode,0)
        self.assertIn('DOWNLOAD_HASH_MISMATCH',r.stdout)
        self.assertFalse(target.exists())
        self.assertEqual(len(list(self.folder.glob('download.exe.part.invalid-*'))),1)

    def test_system_folder_rejected(self):
        r=self.ps("Assert-Destination (Join-Path $env:WINDIR 'new-comfy-test') @() 0")
        self.assertIn('PATH_PROTECTED',r.stdout)

    def test_scan_finds_manual_and_portable_without_models(self):
        manual=self.folder/'manual'
        portable=self.folder/'portable'
        for root in (manual,portable/'ComfyUI'):
            (root/'comfy').mkdir(parents=True)
            (root/'main.py').write_text('')
        (portable/'python_embeded').mkdir()
        (portable/'python_embeded/python.exe').write_text('')
        r=self.ps(f'@(Find-Installations @({self.quote(self.folder)})) | ConvertTo-Json -Compress')
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        data=json.loads(r.stdout)
        self.assertEqual(len(data),2)
        self.assertEqual(sorted(x['portable'] for x in data),[False,True])

    def profile(self,cap,driver,cuda=''):
        return self.ps(f"$h=[pscustomobject]@{{vendor='nvidia';compute='{cap}';driver='{driver}'}}; Select-Profile $h (Read-Config 'compatibility_matrix') '{cuda}'")

    def test_modern_gpu_uses_cuda13(self):
        r=self.profile('8.9','581.42')
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        self.assertEqual(r.stdout.strip(),'nvidia')

    def test_pascal_uses_cuda126(self):
        self.assertEqual(self.profile('6.1','580.0').stdout.strip(),'nvidia_cu126')

    def test_blackwell_rejects_cuda126(self):
        r=self.profile('12.0','581.42','12.6')
        self.assertIn('GPU_ARCHITECTURE_UNSUPPORTED',r.stdout)

    def test_old_driver_blocks(self):
        self.assertIn('DRIVER_TOO_OLD',self.profile('8.9','527.0').stdout)

    def test_unknown_capability_blocks(self):
        self.assertIn('GPU_CAPABILITY_UNKNOWN',self.profile('','581.42').stdout)

    def test_cuda12_driver_boundary(self):
        self.assertIn('DRIVER_TOO_OLD',self.profile('6.1','528.32').stdout)
        self.assertEqual(self.profile('6.1','528.33').stdout.strip(),'nvidia_cu126')

    def test_invalid_hash_manifest_never_downloads(self):
        r=self.ps(f"Get-VerifiedDownload ([pscustomobject]@{{url='https://example.invalid/file';sha256='bad'}}) {self.quote(self.folder/'file')}")
        self.assertIn('DOWNLOAD_MANIFEST_INVALID',r.stdout)
        self.assertFalse((self.folder/'file').exists())

    def test_cancel_folder_does_not_install(self):
        r=self.ps("function Get-Hardware { [pscustomobject]@{vendor='nvidia'} }; function Find-Installations { @() }; function Select-Folder { $null }; Invoke-Setup @()")
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        self.assertEqual(r.stdout.strip().splitlines()[-1],'2')


if __name__=='__main__': unittest.main()
