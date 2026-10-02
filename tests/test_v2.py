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
    def test_recommended_catalog_matches_2x_defaults(self):
        nodes=config.nodos()
        # Same default answers as 2.7.0: Manager, Cine con IA, monitor, video and interface groups.
        self.assertEqual({k for k,v in nodes.items() if v['recommended']},
                         {'manager','cineconia','monitor','kjnodes','vhs','gguf','selflift','h3upscaler','rgthree','customscripts'})
        self.assertFalse(any(nodes[k]['recommended'] for k in ('essentials','comfyroll','was','controlnet_aux','nunchaku')))
        # Our own nodes follow their branch; third-party nodes are pinned.
        self.assertIsNone(nodes['cineconia']['version'])
        self.assertTrue(all(len(n['version'])==40 for k,n in nodes.items() if k!='cineconia'))

    def test_invalid_revision_rejected(self):
        data={'x':{'repo':'https://github.com/a/b.git','carpetas':['b'],'version':'main'}}
        with patch.object(config,'cargar',return_value=data):
            with self.assertRaisesRegex(ValueError,'NODE_REVISION_INVALID'):
                config.nodos()

    def test_seven_zip_download_is_versioned(self):
        url=config.cargar('compatibility_matrix')['tools']['7zr']['url']
        # An unversioned URL changes with each 7-Zip release and breaks the pinned hash.
        self.assertRegex(url,r'/releases/download/[\d.]+/7zr\.exe$')

    def test_vram_rounding_and_unknown(self):
        self.assertIsNone(config.perfil_vram(None))
        self.assertEqual(config.perfil_vram(15.9)['name'],'16 GB')
        self.assertEqual(config.perfil_vram(4)['name'],'<8 GB')
        self.assertEqual(config.perfil_vram(96)['name'],'64 GB+')

    def test_direct_invocation_requires_explicit_consent(self):
        with patch.dict(os.environ,{'CINECONIA_LANG':'es'},clear=True),contextlib.redirect_stdout(io.StringIO()):
            self.assertFalse(config.autorizar('C:/old',lambda _:''))
            self.assertFalse(config.autorizar('C:/old',lambda _:'yes'))
            self.assertTrue(config.autorizar('C:/old',lambda _:'CONFIRMAR'))

    def test_confirmation_word_follows_language(self):
        with patch.dict(os.environ,{'CINECONIA_LANG':'en'},clear=True),contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(config.autorizar('C:/old',lambda _:'CONFIRM'))
            self.assertFalse(config.autorizar('C:/old',lambda _:'confirm'))

    def test_coded_errors_are_explained(self):
        with patch.dict(os.environ,{'CINECONIA_LANG':'es'}):
            text=config.mensaje_error(RuntimeError('DRIVER_TOO_OLD: 580.0'))
            self.assertIn('580.0',text)
            self.assertIn('nvidia.com/drivers',text)
            self.assertIn('DRIVER_TOO_OLD',text)  # the code stays visible for support
            self.assertEqual(config.mensaje_error(OSError('disk full')),'disk full')

    def test_every_error_code_has_both_translations(self):
        es=json.loads((ROOT/'src/locales/es.json').read_text(encoding='utf-8'))
        source=(ROOT/'src/bootstrap.ps1').read_text(encoding='ascii')+(ROOT/'src/configuracion.py').read_text(encoding='utf-8')
        import re
        codes=set(re.findall(r"""throw ["']([A-Z][A-Z0-9_]+)""",source))|set(re.findall(r"""Error\(f?['"]([A-Z][A-Z0-9_]+)""",source))
        self.assertGreater(len(codes),20)
        self.assertEqual(sorted(c for c in codes if 'setup.error.'+c not in es),[])

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
            self.assertTrue(ins.instalar_nodo('new','python','monitor'))
            self.assertFalse(ins.instalar_nodo('new','python','essentials'))
            self.assertEqual([c.args[2] for c in clone.call_args_list],['cineconia','monitor'])

    def test_recommended_groups_install_without_prompt(self):
        ins.ESTADOS_NODOS.clear()
        with patch.dict(os.environ,{'CINECONIA_MODE':'recommended'}),patch.object(ins,'ruta_nodo',return_value=None),patch.object(ins.preflight,'git_exe',return_value='git'),patch.object(ins,'preguntar',side_effect=AssertionError('prompt')),patch.object(ins,'clonar_nodo',return_value=True) as clone,contextlib.redirect_stdout(io.StringIO()):
            _,accepted=ins.instalar_grupo('new','python','video')
            self.assertTrue(accepted)
            self.assertEqual({c.args[2] for c in clone.call_args_list},{'kjnodes','vhs','gguf','selflift','h3upscaler'})
            clone.reset_mock()
            ins.instalar_grupo('new','python','interfaz')
            self.assertEqual({c.args[2] for c in clone.call_args_list},{'rgthree','customscripts'})
            clone.reset_mock()
            # Heavy community nodes stay in advanced mode.
            _,accepted=ins.instalar_grupo('new','python','comunidad')
            self.assertIsNone(accepted)
            clone.assert_not_called()

    def run_clone(self,key):
        commands=[]
        def run(cmd,*args,**kwargs):
            commands.append(cmd)
            if cmd[1]=='clone':
                Path(cmd[-1],'__init__.py').write_text('')
            return True,[]
        with tempfile.TemporaryDirectory() as folder,contextlib.redirect_stdout(io.StringIO()):
            with patch.object(ins.preflight,'git_exe',return_value='git'),patch.object(ins.pasos,'correr',side_effect=run),patch.object(ins,'proteger_torch',return_value=True):
                self.assertTrue(ins.clonar_nodo(folder,'python',key))
        return commands

    def test_pinned_node_stays_on_its_branch(self):
        commands=self.run_clone('kjnodes')
        self.assertIn('--filter=blob:none',commands[0])
        self.assertIn('--no-checkout',commands[0])
        self.assertEqual(commands[1][-3:],['reset','--hard',ins.NODOS['kjnodes']['version']])
        # A detached checkout breaks "git pull --ff-only" in the update launchers.
        self.assertFalse(any('--detach' in c for c in commands))

    def test_own_nodes_follow_latest(self):
        commands=self.run_clone('cineconia')
        self.assertEqual(len(commands),1)
        self.assertIn('--depth',commands[0])

    def test_gpu_kernel_failure_not_success(self):
        with patch.object(verificacion.subprocess,'run',return_value=subprocess.CompletedProcess([],1,'','no kernel image')):
            ok,detail=verificacion.comprobar_gpu('python','nvidia')
            self.assertFalse(ok)
            self.assertIn('no kernel',detail)

    def test_desktop_shortcut_avoids_overwriting(self):
        with patch.object(lanzadores,'_copiar_icono',return_value=None),patch.object(lanzadores.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'ComfyUI (2)\n','')) as run:
            ok,name=lanzadores.crear_acceso_escritorio('C:/new','C:/new/start.bat')
        script=run.call_args.args[0][-1]
        self.assertIn('while(Test-Path -LiteralPath $p)',script)
        self.assertNotIn("Join-Path $d 'ComfyUI.lnk'",script)
        # Plain "ComfyUI", as in 2.x: no channel branding on the desktop.
        self.assertIn("$base='ComfyUI'",script)
        self.assertEqual((ok,name),(True,'ComfyUI (2)'))

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

    def test_fresh_portable_models_folder_is_not_a_library(self):
        with tempfile.TemporaryDirectory() as folder:
            models=Path(folder,'models')
            (models/'checkpoints').mkdir(parents=True); (models/'checkpoints/put_checkpoints_here').write_text('')
            (models/'vae_approx').mkdir(); (models/'vae_approx/taesd_decoder.safetensors').write_bytes(b'x'*100)
            self.assertFalse(modelos_enlace.tiene_modelos(str(models)))
            (models/'loras/style').mkdir(parents=True); (models/'loras/style/look.safetensors').write_bytes(b'x')
            self.assertTrue(modelos_enlace.tiene_modelos(str(models)))

    def test_registered_library_is_linked_after_reinstall(self):
        # The previous ComfyUI was deleted; its library on another disk stays registered.
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder)
            library=base/'E'/'models'; (library/'checkpoints').mkdir(parents=True)
            (library/'checkpoints/model.safetensors').write_bytes(b'x'*10)
            empty=base/'old'/'ComfyUI'/'models'; (empty/'vae_approx').mkdir(parents=True)
            (empty/'vae_approx/taesd_decoder.safetensors').write_bytes(b'x'*10)
            new=base/'new'; (new/'ComfyUI').mkdir(parents=True)
            answers=[]
            def ask(text,options,default=1):
                answers.append([label for label,_ in options])
                return 1
            with patch.dict(os.environ,{'CINECONIA_MODE':'recommended','CINECONIA_LANG':'es'}),\
                 patch.object(ins.modelos_enlace,'bibliotecas_guardadas',return_value=[str(library)]),\
                 patch.object(ins.modelos_enlace,'detectar_instalaciones',return_value=[str(library),str(empty)]),\
                 patch.object(ins.modelos_enlace,'registrar_biblioteca'),\
                 patch.object(ins,'preguntar',side_effect=ask),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(ins.ofrecer_enlace_modelos(str(new)),'linked')
            # One question (use them where they are, Enter); no "which library".
            self.assertEqual(len(answers),1)
            content=(new/'ComfyUI/extra_model_paths.yaml').read_text(encoding='utf-8')
            self.assertIn(str(library).replace('\\','/'),content)
            self.assertIn('is_default: true',content)

    def test_checkout_failure_preserves_incomplete_user_node(self):
        with tempfile.TemporaryDirectory() as folder,contextlib.redirect_stdout(io.StringIO()):
            old=Path(folder,'ComfyUI/custom_nodes/comfyui-kjnodes')
            old.mkdir(parents=True); (old/'user.txt').write_text('preserve')
            def run(cmd,*args,**kwargs):
                if cmd[1]=='clone':
                    Path(cmd[-1],'__init__.py').write_text('')
                    return True,[]
                return False,['pinned revision unavailable']
            with patch.object(ins.preflight,'git_exe',return_value='git'),patch.object(ins.pasos,'correr',side_effect=run):
                self.assertFalse(ins.clonar_nodo(folder,'python','kjnodes'))
            self.assertEqual((old/'user.txt').read_text(),'preserve')


PS=shutil.which('powershell.exe')


@unittest.skipUnless(PS,'Windows PowerShell required')
class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        # Long name: GitHub runners report TEMP as C:\Users\RUNNER~1, while
        # PowerShell returns C:\Users\runneradmin for the same folder.
        self.folder=Path(os.path.realpath(self.tmp.name))

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
function Invoke-Console($FilePath, $ArgumentList) {
    $stage=$ArgumentList[([Array]::IndexOf($ArgumentList,'-Destino')+1)]
    [IO.Directory]::CreateDirectory((Join-Path $stage 'portable/python_embeded')) | Out-Null
    [IO.Directory]::CreateDirectory((Join-Path $stage 'portable/ComfyUI')) | Out-Null
    [IO.File]::WriteAllText((Join-Path $stage 'portable/python_embeded/python.exe'),'')
    [IO.File]::WriteAllText((Join-Path $stage 'portable/ComfyUI/main.py'),'')
    [IO.File]::WriteAllText((Join-Path $target 'user.txt'),'data')
    return 0
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
function Invoke-Console($FilePath, $ArgumentList) {
    $partial=$ArgumentList[([Array]::IndexOf($ArgumentList,'-Salida')+1)]
    [IO.File]::WriteAllText($partial,'corrupt')
    return 0
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

    def test_old_driver_on_modern_card_uses_cuda126_with_notice(self):
        r=self.ps("$h=[pscustomobject]@{vendor='nvidia';compute='8.9';driver='560.94'}; Select-Profile $h (Read-Config 'compatibility_matrix') ''; $script:DriverNotice")
        self.assertEqual(r.stdout.split(),['nvidia_cu126','560.94'])
        r=self.ps("$h=[pscustomobject]@{vendor='nvidia';compute='8.9';driver='581.42'}; Select-Profile $h (Read-Config 'compatibility_matrix') ''; [string]$script:DriverNotice")
        self.assertEqual(r.stdout.split(),['nvidia'])

    def test_cancel_folder_does_not_install(self):
        r=self.ps("function Get-Hardware { [pscustomobject]@{vendor='nvidia'} }; function Select-Profile { 'nvidia' }; function Find-Installations { @() }; function Read-Choice { 'c' }; function Select-Folder { $null }; Invoke-Setup @()")
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        self.assertEqual(r.stdout.strip().splitlines()[-1],'2')

    def test_keeping_existing_installation_asks_once(self):
        code=("$global:asked=0; function Get-Hardware { [pscustomobject]@{vendor='nvidia'} }; "
              "function Find-Installations { @([pscustomobject]@{root='C:\\A'},[pscustomobject]@{root='C:\\B'}) }; "
              "function Read-Choice { $global:asked++; '' }; function Select-Folder { throw 'unexpected' }; "
              "$r=Invoke-Setup @('--lang','en'); \"result=$r asked=$global:asked\"")
        r=self.ps(code)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        # Keeping an installation does not ask which one: nothing is changed.
        self.assertIn('result=0 asked=1',r.stdout)

    def test_default_destination_gets_a_free_name(self):
        r=self.ps(f"Get-FreeDestination {self.quote(self.folder)}")
        self.assertEqual(r.stdout.strip(),str(self.folder/'ComfyUI'))
        (self.folder/'ComfyUI').mkdir()
        r=self.ps(f"Get-FreeDestination {self.quote(self.folder)}")
        self.assertEqual(r.stdout.strip(),str(self.folder/'ComfyUI'))  # empty folder is reused
        (self.folder/'ComfyUI/main.py').write_text('')
        r=self.ps(f"Get-FreeDestination {self.quote(self.folder)}")
        self.assertEqual(r.stdout.strip(),str(self.folder/'ComfyUI-2'))

    def test_rejected_folder_asks_again(self):
        bad=self.folder/'Peña'
        good=self.folder/'ok'
        code=(f"function Get-DefaultParent {{ [pscustomobject]@{{root={self.quote(bad)};free=100GB;media='SSD'}} }}; "
              f"function Read-Choice {{ '' }}; function Select-Folder {{ {self.quote(good)} }}; "
              "Initialize-Language 'en'; Select-Destination @() 0")
        r=self.ps(code)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        self.assertIn('accents',r.stdout)  # the reason, not just a code
        self.assertEqual(r.stdout.strip().splitlines()[-1],str(good/'ComfyUI'))
        self.assertFalse((good/'ComfyUI').exists())

    def test_onedrive_and_accents_rejected(self):
        cloud=self.folder/'OneDrive'
        r=self.ps(f"$env:OneDrive={self.quote(cloud)}; Assert-Destination {self.quote(cloud/'IA')} @() 0")
        self.assertIn('PATH_ONEDRIVE',r.stdout)
        r=self.ps(f"Assert-Destination {self.quote(self.folder/'Ramírez')} @() 0")
        self.assertIn('PATH_NON_ASCII',r.stdout)

    def test_write_probe_leaves_nothing_behind(self):
        new=self.folder/'a/b/ComfyUI'
        r=self.ps(f"Assert-Destination {self.quote(new)} @() 0")
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        self.assertEqual(list(self.folder.iterdir()),[])

    def test_cache_removed_after_extraction(self):
        cache=self.folder/'.cineconia-cache'; cache.mkdir()
        for name in ('v0.38.0-nvidia.7z','7zr.exe'): (cache/name).write_text('x')
        r=self.ps(f"Remove-DownloadCache {self.quote(cache)} @({self.quote(cache/'v0.38.0-nvidia.7z')},{self.quote(cache/'7zr.exe')})")
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        self.assertFalse(cache.exists())

    def test_scan_skips_links_but_not_onedrive_style_folders(self):
        target=self.folder/'target'; (target/'ComfyUI/comfy').mkdir(parents=True)
        (target/'ComfyUI/main.py').write_text('')
        link=self.folder/'link'
        subprocess.run(['cmd','/c','mklink','/J',str(link),str(target)],capture_output=True)
        r=self.ps(f'@(Find-Installations @({self.quote(self.folder)})) | ForEach-Object {{ $_.root }}')
        self.assertEqual(r.stdout.split(),[str(target)])

    def test_arguments_quoted_for_child_processes(self):
        r=self.ps("(@('a','b c','','x\"y','D:\\dir with space\\') | ForEach-Object { Format-Argument $_ }) -join '|'")
        self.assertEqual(r.stdout.strip(),'a|"b c"|""|"x\\"y"|"D:\\dir with space\\\\"')
        r=self.ps("Invoke-Console (Join-Path $PSHOME 'powershell.exe') @('-NoProfile','-Command','exit 7')")
        self.assertEqual(r.stdout.strip(),'7')


if __name__=='__main__': unittest.main()
