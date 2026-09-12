"""Codex: create a disposable exit-test copy; no process launch, no source writes."""
import argparse
from pathlib import Path
import shutil
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    args = parser.parse_args()
    source = args.source.resolve()
    parent = Path(tempfile.mkdtemp(prefix='codex-farewell-'))
    repo = parent / 'fixture'
    avatar = repo / 'apps/avatar-runtime'
    shutil.copytree(source/'apps/avatar-runtime', avatar,
                    ignore=shutil.ignore_patterns('shader_cache','*.log'))
    scripts = repo/'scripts'
    (scripts/'tests').mkdir(parents=True)
    for name in ('start-mvp.ps1','startup-common.ps1','tts-lifecycle.ps1','core_watchdog.ps1','run-avatar-runtime.ps1'):
        shutil.copy2(source/'scripts'/name, scripts/name)
    shutil.copy2(source/'scripts/tests/startup-driver.ps1',scripts/'startup-driver.ps1')
    shutil.copy2(source/'scripts/tests/test_farewell_exit.py',scripts/'tests/test_farewell_exit.py')
    shutil.copy2(source/'start-anime-agent.cmd',repo/'start-anime-agent.cmd')
    for name in ('.farewell-test-fixture','.startup-test-fixture'):
        (repo/name).write_text('Disposable Codex test fixture.\n',encoding='utf-8')
    (repo/'.env').write_text('LLM_PROVIDER=mock\nANIME_AGENT_TTS=0\nANIME_AGENT_WAKE_WORD=0\nANIME_AGENT_MCP_SERVERS=\n',encoding='utf-8')
    project = avatar/'project.godot'
    text = project.read_text(encoding='utf-8')
    assert 'config/name="Luo Tianyi Desktop Avatar MVP"' in text
    text = text.replace('config/name="Luo Tianyi Desktop Avatar MVP"',f'config/name="Codex Farewell {parent.name}"')
    text = text.replace('window/size/always_on_top=true', 'window/size/always_on_top=false')
    text = text.replace('[display]', '[display]\nwindow/size/no_focus=true\nwindow/size/initial_position_type=0\nwindow/size/initial_position=Vector2i(-100,-100)\nwindow/vsync/vsync_mode=0')
    project.write_text(text,encoding='utf-8')
    launcher = avatar/'launcher.gd'
    text = launcher.read_text(encoding='utf-8')
    assert '\troot.add_child(scene.instantiate())' in text
    text = text.replace('\troot.add_child(scene.instantiate())', '\tvar runtime = scene.instantiate()\n\truntime.set_script(load("res://mocap/farewell/exit_probe.gd"))\n\tEngine.max_fps = 20\n\tAudioServer.set_bus_mute(0, true)\n\troot.add_child(runtime)')
    launcher.write_text(text,encoding='utf-8')
    assert not (parent/'tianyi-tts').exists()
    print(repo)


if __name__ == '__main__':
    main()
