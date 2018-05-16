from __future__ import (absolute_import, division, print_function)

__metaclass__ = type
from ansible.plugins.action import ActionBase
import subprocess
import os


class ActionModule(ActionBase):
    TRANSFERS_FILES = False

    def run(self, tmp=None, task_vars=None):

        if task_vars is None:
            task_vars = dict()

        if "all" in self._task.args:
            all = self._task.args.get("all")
            if str(all).lower() in ["true", "yes"]:
                all = True
        else:
            all = False

        if "user" in self._task.args:
            user = self._task.args.get("user")
        else:
            user = False

        command = "ps -ef | grep -vn ' grep ' | %s | awk '{print \"sudo -n kill -9\", $2}' | sh"

        if user:
            grep = "grep sshd | grep '%s'" % user
            command += " && echo OTHERUSER"
        elif all:
            grep = "grep sshd:"
        else:
            grep = "grep sshd: | grep `whoami`"

        command += " && exit"

        sub = subprocess.Popen(
            ["ssh", "-C",
             "-o", "ControlMaster=auto",
             "-o", "ControlPersist=60s",
             "-o", "StrictHostKeyChecking=no",
             "-o", 'IdentityFile="%s"' % self._play_context.private_key_file,
             "-o", "KbdInteractiveAuthentication=no",
             "-o", "PreferredAuthentications=gssapi-with-mic,gssapi-keyex,hostbased,publickey",
             "-o", "PasswordAuthentication=no",
             "-o", "User=%s" % self._play_context.remote_user,
             "-o", "ConnectTimeout=%s" % self._play_context.timeout,
             "-o", "ControlPath=%s" % self._connection.control_path,
             self._connection.host,
             command % grep],
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)

        out, err = sub.communicate()
        out = out.decode('utf-8')
        err = err.decode('utf-8')

        os.system('stty sane')

        result = super(ActionModule, self).run(tmp, task_vars)
        if any(x in err for x in ['Write failed: Broken pipe', "Shared connection to",
                                  "Connection to %s closed by remote host" % self._connection.host]) \
                or "OTHERUSER" in out:
            result['failed'] = False
        else:
            result['failed'] = True
            result['msg'] = err

        return result
