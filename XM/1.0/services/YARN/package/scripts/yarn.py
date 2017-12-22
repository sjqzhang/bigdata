"""
Licensed to the Apache Software Foundation (ASF) under one
or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.  The ASF licenses this file
to you under the Apache License, Version 2.0 (the
"License"); you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Ambari Agent

"""

# Python Imports
import os

# Ambari Common and Resource Management Imports
from resource_management.libraries.script.script import Script
from resource_management.core.resources.service import ServiceConfig
from resource_management.libraries.functions.format import format
from resource_management.libraries.functions.is_empty import is_empty
from resource_management.core.resources.system import Directory
from resource_management.core.resources.system import File
from resource_management.libraries.resources.xml_config import XmlConfig
from resource_management.core.source import InlineTemplate, Template

from resource_management.libraries.functions.mounted_dirs_helper import handle_mounted_dirs

from resource_management.core.resources.system import Execute


def install_hadoop(first=False):
    import params
    Directory(
        params.yarn_log_dir_prefix + '/' + params.yarn_user,
        owner=params.yarn_user,
        group=params.user_group,
        create_parents=True,
        mode=0755)
    Directory(
        params.yarn_log_dir_prefix + '/' + params.mapred_user,
        owner=params.yarn_user,
        group=params.user_group,
        create_parents=True,
        mode=0755)
    Directory(
        params.mapred_log_dir_prefix + '/' + params.mapred_user,
        owner=params.mapred_user,
        group=params.user_group,
        create_parents=True,
        mode=0755)
    Directory(
        params.hdfs_log_dir_prefix,
        owner=params.hdfs_user,
        group=params.user_group,
        create_parents=True,
        mode=0755)

    if not os.path.exists('/opt/' + params.version_dir) or not os.path.exists(params.install_dir):
        Execute('rm -rf %s' %  '/opt/' + params.version_dir)
        Execute('rm -rf %s' % params.install_dir)
        Execute('/bin/rm -f /tmp/' + params.filename)
        Execute(
            'wget ' + params.download_url + ' -O /tmp/' + params.filename,
            user=params.yarn_user)
        Execute('tar -zxf /tmp/' + params.filename + ' -C /opt')
        Execute('ln -s /opt/' + params.version_dir + ' ' + params.install_dir)
        Execute(' rm -rf ' + params.install_dir + '/etc/hadoop')
        Execute('ln -s ' + params.config_path + ' ' + params.install_dir +
                '/etc/hadoop')
        Execute("echo 'export PATH=%s/bin:$PATH'>>/etc/profile.d/hadoop.sh" %
                params.install_dir)
        Execute('mkdir ' + params.install_dir + '/logs && chmod 777 ' +
                params.install_dir + '/logs')
        Execute('chown -R %s:%s /opt/%s' %
                (params.yarn_user, params.user_group, params.version_dir))
        Execute('chown -R %s:%s %s' %
                (params.yarn_user, params.user_group, params.install_dir))
        Execute('chown root:%s %s/bin/container-executor' %(params.user_group,params.install_dir))
        Execute('/bin/rm -f /tmp/' + params.filename)

def yarn(name=None, config_dir=None):
    """
  :param name: Component name, apptimelineserver, nodemanager, resourcemanager, or None (defaults for client)
  :param config_dir: Which config directory to write configs to, which could be different during rolling upgrade.
  """
    import params

    if name == 'resourcemanager':
        setup_resourcemanager()
    elif name == 'nodemanager':
        setup_nodemanager()
    elif name == 'apptimelineserver':
        setup_ats()
    elif name == 'historyserver':
        setup_historyserver()

    if config_dir is None:
        config_dir = params.hadoop_conf_dir

    Directory(
        params.hadoop_conf_dir,
        create_parents=True,
        owner='root',
        group='root')

    if params.yarn_nodemanager_recovery_dir:
        Directory(
            InlineTemplate(params.yarn_nodemanager_recovery_dir).get_content(),
            owner=params.yarn_user,
            group=params.user_group,
            create_parents=True,
            mode=0755,
            cd_access='a', )

    Directory(
        [params.yarn_pid_dir_prefix, params.yarn_pid_dir, params.yarn_log_dir],
        owner=params.yarn_user,
        group=params.user_group,
        create_parents=True,
        cd_access='a', )

    Directory(
        [params.mapred_pid_dir_prefix, params.mapred_pid_dir,
         params.mapred_log_dir_prefix, params.mapred_log_dir],
        owner=params.mapred_user,
        group=params.user_group,
        create_parents=True,
        cd_access='a', )
    Directory(
        [params.yarn_log_dir_prefix],
        owner=params.yarn_user,
        group=params.user_group,
        create_parents=True,
        ignore_failures=True,
        cd_access='a', )

    XmlConfig(
        "core-site.xml",
        conf_dir=config_dir,
        configurations=params.config['configurations']['core-site'],
        configuration_attributes=params.config['configuration_attributes'][
            'core-site'], owner=params.hdfs_user, group=params.user_group,
        mode=0644)

    # During RU, Core Masters and Slaves need hdfs-site.xml
    # TODO, instead of specifying individual configs, which is susceptible to breaking when new configs are added,
    # RU should rely on all available in <stack-root>/<version>/hadoop/conf
    XmlConfig(
        "hdfs-site.xml",
        conf_dir=config_dir,
        configurations=params.config['configurations']['hdfs-site'],
        configuration_attributes=params.config['configuration_attributes'][
            'hdfs-site'], owner=params.hdfs_user, group=params.user_group,
        mode=0644)

    XmlConfig(
        "mapred-site.xml",
        conf_dir=config_dir,
        configurations=params.config['configurations']['mapred-site'],
        configuration_attributes=params.config['configuration_attributes'][
            'mapred-site'], owner=params.yarn_user, group=params.user_group,
        mode=0644)

    XmlConfig(
        "yarn-site.xml",
        conf_dir=config_dir,
        configurations=params.config['configurations']['yarn-site'],
        configuration_attributes=params.config['configuration_attributes'][
            'yarn-site'], owner=params.yarn_user, group=params.user_group,
        mode=0644)

    XmlConfig(
        "capacity-scheduler.xml",
        conf_dir=config_dir,
        configurations=params.config['configurations']['capacity-scheduler'],
        configuration_attributes=params.config['configuration_attributes'][
            'capacity-scheduler'], owner=params.yarn_user,
        group=params.user_group, mode=0644)

    File(
        format("{limits_conf_dir}/yarn.conf"),
        mode=0644,
        content=Template('yarn.conf.j2'))

    File(
        format("{limits_conf_dir}/mapreduce.conf"),
        mode=0644,
        content=Template('mapreduce.conf.j2'))

    File(
        os.path.join(config_dir, "yarn-env.sh"),
        owner=params.yarn_user,
        group=params.user_group,
        mode=0755,
        content=InlineTemplate(params.yarn_env_sh_template))

    File(
        format("{yarn_container_bin}/container-executor"),
        owner='root',
        group=params.yarn_executor_container_group,
        mode=params.container_executor_mode)

    File(
        os.path.join(config_dir, "container-executor.cfg"),
        group=params.user_group,
        mode=0644,
        content=Template('container-executor.cfg.j2'))

    Directory(
        params.cgroups_dir,
        owner=params.yarn_user,
        group=params.user_group,
        create_parents=True,
        mode=0755,
        cd_access="a")

    File(
        os.path.join(config_dir, "mapred-env.sh"),
        owner=params.tc_owner,
        mode=0755,
        content=InlineTemplate(params.mapred_env_sh_template))

    if params.security_enabled:
        File(
            os.path.join(params.hadoop_bin, "task-controller"),
            owner="root",
            group=params.mapred_tt_group,
            mode=06050)
        File(
            os.path.join(config_dir, 'taskcontroller.cfg'),
            owner=params.tc_owner,
            mode=params.tc_mode,
            group=params.mapred_tt_group,
            content=Template("taskcontroller.cfg.j2"))
        File(
            os.path.join(config_dir, 'yarn_jaas.conf'),
            owner=params.yarn_user,
            group=params.user_group,
            content=Template("yarn_jaas.conf.j2"))
    else:
        File(
            os.path.join(config_dir, 'taskcontroller.cfg'),
            owner=params.tc_owner,
            content=Template("taskcontroller.cfg.j2"))

    XmlConfig(
        "mapred-site.xml",
        conf_dir=config_dir,
        configurations=params.config['configurations']['mapred-site'],
        configuration_attributes=params.config['configuration_attributes'][
            'mapred-site'], owner=params.mapred_user, group=params.user_group)

    XmlConfig(
        "capacity-scheduler.xml",
        conf_dir=config_dir,
        configurations=params.config['configurations']['capacity-scheduler'],
        configuration_attributes=params.config['configuration_attributes'][
            'capacity-scheduler'], owner=params.hdfs_user,
        group=params.user_group)

    if "ssl-client" in params.config['configurations']:
        XmlConfig(
            "ssl-client.xml",
            conf_dir=config_dir,
            configurations=params.config['configurations']['ssl-client'],
            configuration_attributes=params.config['configuration_attributes'][
                'ssl-client'], owner=params.hdfs_user, group=params.user_group)

        Directory(
            params.hadoop_conf_secure_dir,
            create_parents=True,
            owner='root',
            group=params.user_group,
            cd_access='a', )

        XmlConfig(
            "ssl-client.xml",
            conf_dir=params.hadoop_conf_secure_dir,
            configurations=params.config['configurations']['ssl-client'],
            configuration_attributes=params.config['configuration_attributes'][
                'ssl-client'], owner=params.hdfs_user, group=params.user_group)

    if "ssl-server" in params.config['configurations']:
        XmlConfig(
            "ssl-server.xml",
            conf_dir=config_dir,
            configurations=params.config['configurations']['ssl-server'],
            configuration_attributes=params.config['configuration_attributes'][
                'ssl-server'], owner=params.hdfs_user, group=params.user_group)
    if os.path.exists(os.path.join(config_dir, 'fair-scheduler.xml')):
        File(
            os.path.join(config_dir, 'fair-scheduler.xml'),
            owner=params.mapred_user,
            group=params.user_group)

    if os.path.exists(os.path.join(config_dir, 'ssl-client.xml.example')):
        File(
            os.path.join(config_dir, 'ssl-client.xml.example'),
            owner=params.mapred_user,
            group=params.user_group)

    if os.path.exists(os.path.join(config_dir, 'ssl-server.xml.example')):
        File(
            os.path.join(config_dir, 'ssl-server.xml.example'),
            owner=params.mapred_user,
            group=params.user_group)


def setup_historyserver():
    import params

    if params.yarn_log_aggregation_enabled:
        params.HdfsResource(
            params.yarn_nm_app_log_dir,
            action="create_on_execute",
            type="directory",
            owner=params.yarn_user,
            group=params.user_group,
            mode=01777,
            recursive_chmod=True)

    # create the /tmp folder with proper permissions if it doesn't exist yet
    if params.entity_file_history_directory.startswith('/tmp'):
        params.HdfsResource(
            params.hdfs_tmp_dir,
            action="create_on_execute",
            type="directory",
            owner=params.hdfs_user,
            mode=0777, )

    params.HdfsResource(
        params.entity_file_history_directory,
        action="create_on_execute",
        type="directory",
        owner=params.yarn_user,
        group=params.user_group)
    params.HdfsResource(
        "/mapred",
        type="directory",
        action="create_on_execute",
        owner=params.mapred_user)
    params.HdfsResource(
        "/mapred/system",
        type="directory",
        action="create_on_execute",
        owner=params.hdfs_user)
    params.HdfsResource(
        params.mapreduce_jobhistory_done_dir,
        type="directory",
        action="create_on_execute",
        owner=params.mapred_user,
        group=params.user_group,
        change_permissions_for_parents=True,
        mode=0777)
    params.HdfsResource(None, action="execute")
    Directory(
        params.jhs_leveldb_state_store_dir,
        owner=params.mapred_user,
        group=params.user_group,
        create_parents=True,
        cd_access="a",
        recursive_ownership=True, )


def setup_nodemanager():
    import params
    try:
        Execute('umount /sys/fs/cgroup/cpu,cpuacct')
        Execute('mkdir -p /cgroups/cpu /cgroups/cpuacct')
        Execute('mount -t cgroup -o rw,nosuid,nodev,noexec,relatime,cpu cgroup /cgroups/cpu')
        Execute('mount -t cgroup -o rw,nosuid,nodev,noexec,relatime,cpuacct cgroup /cgroups/cpuacct')
        Execute('chown -R yarn:hadoop /cgroups/cpu/yarn')
    except Exception as e:
        print str(e)

    # First start after enabling/disabling security
    if params.toggle_nm_security:
        Directory(
            params.nm_local_dirs_list + params.nm_log_dirs_list,
            action='delete')

        # If yarn.nodemanager.recovery.dir exists, remove this dir
        if params.yarn_nodemanager_recovery_dir:
            Directory(
                InlineTemplate(params.yarn_nodemanager_recovery_dir)
                .get_content(),
                action='delete')

        # Setting NM marker file
        if params.security_enabled:
            Directory(params.nm_security_marker_dir)
            File(
                params.nm_security_marker,
                content="Marker file to track first start after enabling/disabling security. "
                "During first start yarn local, log dirs are removed and recreated")
        elif not params.security_enabled:
            File(params.nm_security_marker, action="delete")

    if not params.security_enabled or params.toggle_nm_security:
        # handle_mounted_dirs ensures that we don't create dirs which are temporary unavailable (unmounted), and intended to reside on a different mount.
        nm_log_dir_to_mount_file_content = handle_mounted_dirs(
            create_log_dir, params.nm_log_dirs,
            params.nm_log_dir_to_mount_file, params)
        # create a history file used by handle_mounted_dirs
        File(
            params.nm_log_dir_to_mount_file,
            owner=params.hdfs_user,
            group=params.user_group,
            mode=0644,
            content=nm_log_dir_to_mount_file_content)
        nm_local_dir_to_mount_file_content = handle_mounted_dirs(
            create_local_dir, params.nm_local_dirs,
            params.nm_local_dir_to_mount_file, params)
        File(
            params.nm_local_dir_to_mount_file,
            owner=params.hdfs_user,
            group=params.user_group,
            mode=0644,
            content=nm_local_dir_to_mount_file_content)


def setup_resourcemanager():
    import params

    Directory(
        params.rm_nodes_exclude_dir,
        mode=0755,
        create_parents=True,
        cd_access='a', )
    File(
        params.rm_nodes_exclude_path,
        owner=params.yarn_user,
        group=params.user_group)
    File(
        params.yarn_job_summary_log,
        owner=params.yarn_user,
        group=params.user_group)
    if not is_empty(
            params.node_label_enable) and params.node_label_enable or is_empty(
                params.node_label_enable) and params.node_labels_dir:
        params.HdfsResource(
            params.node_labels_dir,
            type="directory",
            action="create_on_execute",
            change_permissions_for_parents=True,
            owner=params.yarn_user,
            group=params.user_group,
            mode=0700)
        params.HdfsResource(None, action="execute")


def setup_ats():
    import params

    Directory(
        params.ats_leveldb_dir,
        owner=params.yarn_user,
        group=params.user_group,
        create_parents=True,
        cd_access="a", )

    # if stack support application timeline-service state store property (timeline_state_store stack feature)
    if params.stack_supports_timeline_state_store:
        Directory(
            params.ats_leveldb_state_store_dir,
            owner=params.yarn_user,
            group=params.user_group,
            create_parents=True,
            cd_access="a", )
    # app timeline server 1.5 directories
    if not is_empty(params.entity_groupfs_store_dir):
        parent_path = os.path.dirname(params.entity_groupfs_store_dir)
        params.HdfsResource(
            parent_path,
            type="directory",
            action="create_on_execute",
            change_permissions_for_parents=True,
            owner=params.yarn_user,
            group=params.user_group,
            mode=0755)
        params.HdfsResource(
            params.entity_groupfs_store_dir,
            type="directory",
            action="create_on_execute",
            owner=params.yarn_user,
            group=params.user_group,
            mode=params.entity_groupfs_store_dir_mode)
    if not is_empty(params.entity_groupfs_active_dir):
        parent_path = os.path.dirname(params.entity_groupfs_active_dir)
        params.HdfsResource(
            parent_path,
            type="directory",
            action="create_on_execute",
            change_permissions_for_parents=True,
            owner=params.yarn_user,
            group=params.user_group,
            mode=0755)
        params.HdfsResource(
            params.entity_groupfs_active_dir,
            type="directory",
            action="create_on_execute",
            owner=params.yarn_user,
            group=params.user_group,
            mode=params.entity_groupfs_active_dir_mode)
    params.HdfsResource(None, action="execute")


def create_log_dir(dir_name):
    import params
    Directory(
        dir_name,
        create_parents=True,
        cd_access="a",
        mode=0775,
        owner=params.yarn_user,
        group=params.user_group,
        ignore_failures=True, )


def create_local_dir(dir_name):
    import params
    Directory(
        dir_name,
        create_parents=True,
        cd_access="a",
        mode=0755,
        owner=params.yarn_user,
        group=params.user_group,
        ignore_failures=True,
        recursive_mode_flags={'f': 'a+rw',
                              'd': 'a+rwx'}, )