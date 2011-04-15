"""
Generic VCS support for Fabric
"""

from fabric.api import local, run, abort

def export(repository_url, export_dir, branch='', repository_type='svn', force=0, log_file='', only_dir=''):
    """
    Exports a project from the source repository to a local folder.
    Example of usage:

        vcs.export(
            repository_type = 'git',
            repository_url = 'some.git.server:/var/git/somerepo.git',
            export_dir = '/var/tmp/export-here-please',
            branch = 'master',
            force = 1,
        )

    The 'force' flag allows to export to an existing directory
    when the repository type is "svn".

    Works with either 'git' or 'svn' repository types.

    Optionally you can supply:

    * a 'log_file' parameter: this will log the export output
      into the specified file

    * a 'only_dir' parameter: will only export a given path from the
      repository instead of the whole file tree.

    """

    # Create the export dir if it doesn't exist
    local('mkdir -p %s' % export_dir)

    if not log_file:
        log_file = '%s/vcs-export.log' % export_dir

    repo_meta = {
        'repo_url' : repository_url,
        'branch' : branch,
        'log_file' : log_file,
        'export_dir' : export_dir,
        'repo_archive_opt' : '',
        'only_dir' : only_dir,
    }

    #
    # Handle multiple VCS systems
    #
    if repository_type == 'svn':

        # Mark svn release
        local('echo "Current source code ref is:" 1> %s' % log_file)
        local('svn info %(repo_url)s 1>> %(log_file)s' % repo_meta)

        svn_export_cmd = 'svn export'
        if force == 1:
            svn_export_cmd = 'svn export --force'

        repo_meta['svn_export_cmd'] = svn_export_cmd

        export_cmd = '%(svn_export_cmd)s %(repo_url)s%(only_dir)s %(export_dir)s/%(branch)s 1>> %(log_file)s' % repo_meta

    elif repository_type == 'git':

        if not branch:
            repo_meta['branch'] = 'master'

        # We also need to create the subdir for the branch, or else tar complains
        local('mkdir -p %(export_dir)s/%(branch)s' % repo_meta)

        if repository_url:

            repo_meta['repo_archive_opt'] = '--remote=' + repository_url

            local('echo "Current source code ref is:" 1> %s' % log_file)
            local('echo "git ls-remote %(repo_url)s %(branch)s" 1>> %(log_file)s' % repo_meta)
            local('git ls-remote %(repo_url)s %(branch)s 1>> %(log_file)s' % repo_meta)
            local('echo 1>> %s' % log_file)

        else:

            local('echo "Current source code ref is:" 1> %s' % log_file)
            local('echo "git rev-parse %(branch)s" 1>> %(log_file)s' % repo_meta)
            local('git rev-parse %(branch)s 1>> %(log_file)s' % repo_meta)
            local('echo 1>> %s' % log_file)

        export_cmd = 'git archive --prefix=%(branch)s/ %(repo_archive_opt)s %(branch)s %(only_dir)s | tar xvC %(export_dir)s 1>> %(log_file)s' % repo_meta

    else:
        abort("%s repository support is not implemented")

    return local(export_cmd)


def list_tags(repository_url, project='', repository_type='svn'):
    """
    Lists the tags at the specified remote repository

    Example:

        print vcs.list_tags(
            repository_type = 'svn',        # Default
            repository_url = 'http://svn-server/svn/project',
            project = 'project',
        )

    An example with a git repository:

        list = vcs.list_tags(
            'my.git.server:/var/git/repo.git',
            'project',
            'git'
        )

    """

    command = ''

    meta = {
        'repo_url' : repository_url,
        'project'  : project,
    }

    if repository_type == 'svn':
        command = 'svn list %(repo_url)s/tags/'
        if project:
            command += '| grep ^%(project)s'
    elif repository_type == 'git':
        command = 'git ls-remote --tags %(repo_url)s'
        if project:
            command += ' %(project)s\*'

    command = command % meta
    return local(command)


def tag(repository_url, tag, branch='', source_tag='', message='', repository_type='svn'):
    """
    Tag a remote repository, optionally with a message.

    Example:

        vcs.tag(
            # Note: no 'trunk' or branches in the URL
            repository_url = 'http://some.svn.server/svn/project',
            repository_type = 'svn'
            message = 'Some comment',
            tag = 'tag-name',
        )

    Remote tagging for 'git' is implemented through cloning the remote
    repository to a temporary directory, tagging it locally, and
    pushing tags to the origin. As lame as that might be, it's the
    only way I found to do it.

    """

    if not repository_url:
        return

    if not tag:
        return

    tag_meta = {
        'src' : repository_url,
        'tag' : tag,
        'message' : message,
        'branch' : branch,
    }

    if repository_type == 'svn':
        src = repository_url
        dest = src + '/tags/' + tag

        # Messy...
        if source_tag:
            src += '/tags/' + source_tag
        else:
            if not branch or branch == 'trunk':
                src += '/trunk'
            else:
                src += '/branches/' + branch

        tag_meta['src'] = src
        tag_meta['dest'] = dest

        tag_cmd = "svn cp -m '%(message)s' %(src)s %(dest)s"

    elif repository_type == 'git':
        if not branch:
            tag_meta['branch'] = 'master'
        tag_meta['temp_dir'] = "/var/tmp/deployment/repos/temp.$$"
        tag_cmd = \
              'rm -rf %(temp_dir)s && ' \
            + 'git clone --depth=1 %(src)s %(temp_dir)s && ' \
            + 'cd %(temp_dir)s && ' \
            + "git checkout %(branch)s && " \
            + "git tag -a '%(tag)s' -m '%(message)s' && " \
            + "git push origin --tags && " \
            + "rm -rf %(temp_dir)s";

    else:
        print "Tagging in %s not implemented"
        return

    tag_cmd = tag_cmd % tag_meta

    return local(tag_cmd)

