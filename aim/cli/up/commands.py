import os
import click

from aim.web.configs import AIM_UI_DEFAULT_PORT, AIM_UI_DEFAULT_HOST, AIM_TF_LOGS_PATH_KEY, AIM_ENV_MODE_KEY, \
    AIM_UI_MOUNTED_REPO_PATH, AIM_UI_TELEMETRY_KEY
from aim.sdk.repo import Repo, RepoStatus
from aim.sdk.utils import clean_repo_path
from aim.cli.up.utils import build_db_upgrade_command, build_uvicorn_command

from aim.web.utils import exec_cmd
from aim.web.utils import ShellCommandException


@click.command()
@click.option('-h', '--host', default=AIM_UI_DEFAULT_HOST, type=str)
@click.option('-p', '--port', default=AIM_UI_DEFAULT_PORT, type=int)
@click.option('-w', '--workers', default=1, type=int)
@click.option('--repo', required=False, type=click.Path(exists=True,
                                                        file_okay=False,
                                                        dir_okay=True,
                                                        writable=True))
@click.option('--tf_logs', type=click.Path(exists=True, readable=True))
@click.option('--dev', is_flag=True, default=False)
def up(dev, host, port, workers, repo, tf_logs):
    if dev:
        os.environ[AIM_ENV_MODE_KEY] = 'dev'
    else:
        os.environ[AIM_ENV_MODE_KEY] = 'prod'

    repo_path = clean_repo_path(repo) or Repo.default_repo_path()
    repo_status = Repo.check_repo_status(repo_path)
    if repo_status == RepoStatus.MISSING:
        init_repo = click.confirm(f'\'{repo_path}\' is not a valid Aim repository. Do you want to initialize it?')
        if not init_repo:
            click.echo('To initialize repo please run the following command:')
            click.secho('aim init', fg='yellow')
            return
        repo_inst = Repo.from_path(repo_path, init=True)
    elif repo_status == RepoStatus.UPDATE_REQUIRED:
        upgrade_repo = click.confirm(f'\'{repo_path}\' requires upgrade. Do you want to run upgrade automatically?')
        if upgrade_repo:
            from aim.cli.upgrade.utils import convert_2to3
            repo_inst = convert_2to3(repo_path, drop_existing=False, skip_failed_runs=False, skip_checks=False)
        else:
            click.echo('To upgrade repo please run the following command:')
            click.secho(f'aim upgrade --repo {repo_path} 2to3', fg='yellow')
            return
    else:
        repo_inst = Repo.from_path(repo_path)
        if repo_status == RepoStatus.PATCH_REQUIRED:
            repo_inst.structured_db.run_upgrades()

    os.environ[AIM_UI_MOUNTED_REPO_PATH] = repo_inst.path

    if tf_logs:
        os.environ[AIM_TF_LOGS_PATH_KEY] = tf_logs

    try:
        db_cmd = build_db_upgrade_command()
        exec_cmd(db_cmd, stream_output=True)
    except ShellCommandException:
        click.echo('Failed to initialize Aim DB. '
                   'Please see the logs above for details.')
        return

    if dev or (os.getenv(AIM_UI_TELEMETRY_KEY) is not None and os.getenv(AIM_UI_TELEMETRY_KEY) == '0'):
        os.environ[AIM_UI_TELEMETRY_KEY] = '0'
    else:
        os.environ[AIM_UI_TELEMETRY_KEY] = '1'
        alert_msg = 'Aim UI collects anonymous usage analytics.'
        opt_out_msg = 'Read how to opt-out here: '
        opt_out_url = 'https://github.com/aimhubio/aim#anonymized-telemetry'
        line_width = max(len(opt_out_msg), len(alert_msg)) + 16
        click.echo('┌{}┐'.format('-' * (line_width - 2)))
        click.echo('{}{}{}'.format(' ' * ((line_width - len(alert_msg)) // 2),
                                   alert_msg,
                                   ' ' * ((line_width - len(alert_msg)) // 2)))
        click.echo('{}{}{}'.format(' ' * ((line_width - len(opt_out_msg)) // 2),
                                   opt_out_msg,
                                   ' ' * ((line_width - len(opt_out_msg)) // 2)))
        click.echo('{}{}{}'.format(' ' * ((line_width - len(opt_out_url)) // 2),
                                   opt_out_url,
                                   ' ' * ((line_width - len(opt_out_url)) // 2)))
        click.echo('└{}┘'.format('-' * (line_width - 2)))

    click.echo(
        click.style('Running Aim UI on repo `{}`'.format(repo_inst),
                    fg='yellow'))

    click.echo('Open http://{}:{}'.format(host, port))
    click.echo('Press Ctrl+C to exit')

    try:
        server_cmd = build_uvicorn_command(host, port, workers)
        exec_cmd(server_cmd, stream_output=True)
    except ShellCommandException:
        click.echo('Failed to run Aim UI. '
                   'Please see the logs above for details.')
        return
