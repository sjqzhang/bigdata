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

"""
import json
import os
from resource_management.libraries.resources.properties_file import PropertiesFile
from resource_management.core.resources.system import Directory, Execute, File
from resource_management.core.source import DownloadSource
from resource_management.core.source import InlineTemplate
from resource_management.libraries.functions import format
from resource_management.libraries.functions.show_logs import show_logs
from resource_management.core.logger import Logger


def install_druid():
    import params
    Directory(
        [params.druid_conf_dir],
        owner=params.druid_user,
        group=params.user_group,
        mode=0775,
        create_parents=True)
    if not os.path.exists('/opt/' + params.version_dir) or not os.path.exists(params.install_dir):
        Execute('rm -rf %s' %  '/opt/' + params.version_dir)
        Execute('rm -rf %s' % params.install_dir)
        Execute(
            'wget ' + params.download_url + ' -O /tmp/' + params.filename,
            user=params.druid_user)
        Execute('tar -zxf /tmp/' + params.filename + ' -C /opt')
        Execute('ln -s /opt/' + params.version_dir + ' ' + params.install_dir)
        Execute(' rm -rf ' + params.install_dir + '/conf/druid')
        Execute('ln -s ' + params.druid_conf_dir + ' ' + params.install_dir +
                '/conf/druid')
        Execute("echo 'export PATH=%s/bin:$PATH'>>/etc/profile.d/hadoop.sh" %
                params.install_dir)
        Execute('chown -R %s:%s /opt/%s' %
                (params.druid_user, params.user_group, params.version_dir))
        Execute('chown -R %s:%s %s' %
                (params.druid_user, params.user_group, params.install_dir))
        Execute('/bin/rm -f /tmp/' + params.filename)


def druid(upgrade_type=None, nodeType=None):
    import params
    ensure_base_directories()

    # Environment Variables
    File(
        format("{params.druid_conf_dir}/druid-env.sh"),
        owner=params.druid_user,
        content=InlineTemplate(params.druid_env_sh_template),
        mode=0700)
    File(
        format("{params.install_dir}/bin/node.sh"),
        owner=params.druid_user,
        content=InlineTemplate(params.druid_node_content_template),
        mode=0755)

    # common config
    druid_common_config = mutable_config_dict(params.config['configurations'][
        'druid-common'])
    # User cannot override below configs
    druid_common_config['druid.host'] = params.hostname
    druid_common_config[
        'druid.extensions.directory'] = params.druid_extensions_dir
    druid_common_config[
        'druid.extensions.hadoopDependenciesDir'] = params.druid_hadoop_dependencies_dir
    druid_common_config[
        'druid.selectors.indexing.serviceName'] = params.config[
            'configurations']['druid-overlord']['druid.service']
    druid_common_config['druid.selectors.coordinator.serviceName'] = \
      params.config['configurations']['druid-coordinator']['druid.service']
    druid_common_config['druid.extensions.loadList'] = json.dumps(
        eval(params.druid_extensions_load_list) + eval(
            params.druid_security_extensions_load_list))

    # delete the password and user if empty otherwiswe derby will fail.
    if 'derby' == druid_common_config['druid.metadata.storage.type']:
        del druid_common_config['druid.metadata.storage.connector.user']
        del druid_common_config['druid.metadata.storage.connector.password']

    druid_env_config = mutable_config_dict(params.config['configurations'][
        'druid-env'])

    PropertiesFile(
        "common.runtime.properties",
        dir=params.druid_common_conf_dir,
        properties=druid_common_config,
        owner=params.druid_user,
        group=params.user_group,
        mode=0600)
    Logger.info("Created common.runtime.properties")

    File(
        format("{params.druid_common_conf_dir}/log4j2.xml"),
        mode=0644,
        owner=params.druid_user,
        group=params.user_group,
        content=InlineTemplate(params.log4j_props))

    log4j_props_log = '''<?xml version="1.0" encoding="UTF-8" ?>
<Configuration status="WARN">
    <Appenders>
        <Console name="Console" target="SYSTEM_OUT">
            <PatternLayout pattern="%d{ISO8601} %p [%t] %c - %m%n"/>
        </Console>
    </Appenders>
    <Loggers>
        <Root level="info">
            <AppenderRef ref="Console"/>
        </Root>
    </Loggers>
</Configuration>
    '''
    File(
        format("{params.druid_common_conf_dir}/log-task.xml"),
        mode=0644,
        owner=params.druid_user,
        group=params.user_group,
        content=InlineTemplate(log4j_props_log))

    container_log4j_log = '''
# Define some default values that can be overridden by system properties
hadoop.root.logger=DEBUG,CLA
yarn.app.mapreduce.shuffle.logger=${hadoop.root.logger}

# Define the root logger to the system property "hadoop.root.logger".
log4j.rootLogger=${hadoop.root.logger}, EventCounter

# Logging Threshold
log4j.threshold=ALL

#
# ContainerLog Appender
#

#Default values
yarn.app.container.log.dir=null
yarn.app.container.log.filesize=100

hadoop.root.logfile=syslog

log4j.appender.CLA=org.apache.hadoop.yarn.ContainerLogAppender
log4j.appender.CLA.containerLogDir=${yarn.app.container.log.dir}
log4j.appender.CLA.containerLogFile=${hadoop.root.logfile}
log4j.appender.CLA.totalLogFileSize=${yarn.app.container.log.filesize}
log4j.appender.CLA.layout=org.apache.log4j.PatternLayout
log4j.appender.CLA.layout.ConversionPattern=%d{ISO8601} %p [%t] %c: %m%n

log4j.appender.CRLA=org.apache.hadoop.yarn.ContainerRollingLogAppender
log4j.appender.CRLA.containerLogDir=${yarn.app.container.log.dir}
log4j.appender.CRLA.containerLogFile=${hadoop.root.logfile}
log4j.appender.CRLA.maximumFileSize=${yarn.app.container.log.filesize}
log4j.appender.CRLA.maxBackupIndex=${yarn.app.container.log.backups}
log4j.appender.CRLA.layout=org.apache.log4j.PatternLayout
log4j.appender.CRLA.layout.ConversionPattern=%d{ISO8601} %p [%t] %c: %m%n

log4j.appender.shuffleCLA=org.apache.hadoop.yarn.ContainerLogAppender
log4j.appender.shuffleCLA.containerLogDir=${yarn.app.container.log.dir}
log4j.appender.shuffleCLA.containerLogFile=${yarn.app.mapreduce.shuffle.logfile}
log4j.appender.shuffleCLA.totalLogFileSize=${yarn.app.mapreduce.shuffle.log.filesize}
log4j.appender.shuffleCLA.layout=org.apache.log4j.PatternLayout
log4j.appender.shuffleCLA.layout.ConversionPattern=%d{ISO8601} %p [%t] %c: %m%n

log4j.appender.shuffleCRLA=org.apache.hadoop.yarn.ContainerRollingLogAppender
log4j.appender.shuffleCRLA.containerLogDir=${yarn.app.container.log.dir}
log4j.appender.shuffleCRLA.containerLogFile=${yarn.app.mapreduce.shuffle.logfile}
log4j.appender.shuffleCRLA.maximumFileSize=${yarn.app.mapreduce.shuffle.log.filesize}
log4j.appender.shuffleCRLA.maxBackupIndex=${yarn.app.mapreduce.shuffle.log.backups}
log4j.appender.shuffleCRLA.layout=org.apache.log4j.PatternLayout
log4j.appender.shuffleCRLA.layout.ConversionPattern=%d{ISO8601} %p [%t] %c: %m%n

################################################################################
# Shuffle Logger
#
log4j.logger.org.apache.hadoop.mapreduce.task.reduce=${yarn.app.mapreduce.shuffle.logger}
log4j.additivity.org.apache.hadoop.mapreduce.task.reduce=false
# Merger is used for both map-side and reduce-side spill merging. On the map
# side yarn.app.mapreduce.shuffle.logger == hadoop.root.logger
#
log4j.logger.org.apache.hadoop.mapred.Merger=${yarn.app.mapreduce.shuffle.logger}
log4j.additivity.org.apache.hadoop.mapred.Merger=false
#
# Event Counter Appender
# Sends counts of logging messages at different severity levels to Hadoop Metrics.
#
log4j.appender.EventCounter=org.apache.hadoop.log.metrics.EventCounter    
    '''
    File(
        format("{params.druid_common_conf_dir}/container-log4j.properties"),
        mode=0644,
        owner=params.druid_user,
        group=params.user_group,
        content=InlineTemplate(container_log4j_log))

    Logger.info("Created log4j file")

    File(
        "/etc/logrotate.d/druid",
        mode=0644,
        owner='root',
        group='root',
        content=InlineTemplate(params.logrotate_props))

    Logger.info("Created log rotate file")

    # node specific configs
    for node_type in ['coordinator', 'overlord', 'historical', 'broker',
                      'middleManager', 'router']:
        node_config_dir = format('{params.druid_conf_dir}/{node_type}')
        node_type_lowercase = node_type.lower()

        # Write runtime.properties file
        node_config = mutable_config_dict(params.config['configurations'][
            format('druid-{node_type_lowercase}')])
        PropertiesFile(
            "runtime.properties",
            dir=node_config_dir,
            properties=node_config,
            owner=params.druid_user,
            group=params.user_group,
            mode=0600)
        Logger.info(
            format("Created druid-{node_type_lowercase} runtime.properties"))

        # Write jvm configs
        File(
            format('{node_config_dir}/jvm.config'),
            owner=params.druid_user,
            group=params.user_group,
            content=InlineTemplate(
                "-server \n-Xms{{node_heap_memory}}m \n-Xmx{{node_heap_memory}}m \n-XX:MaxDirectMemorySize={{node_direct_memory}}m \n{{node_jvm_opts}} \n-Dfile.encoding=UTF-8 \n-Djava.io.tmpdir={{tmp_log_dir}} \n-Djava.util.logging.manager=org.apache.logging.log4j.jul.LogManager\n-Dlog.file.path={{log_dir}} \n-Dlog.file.type={{node_type}} \n-Ddruid.dir=/opt/druid",
                node_heap_memory=druid_env_config[format('druid.{node_type_lowercase}.jvm.heap.memory')],
                #log4j_config_file=format("{params.druid_common_conf_dir}/log4j2.xml"),
                node_type = node_type_lowercase,
                log_dir = params.druid_log_dir,
                tmp_log_dir = params.druid_log_dir,
                node_direct_memory=druid_env_config[format('druid.{node_type_lowercase}.jvm.direct.memory')],
                node_jvm_opts=druid_env_config[format('druid.{node_type_lowercase}.jvm.opts')]))
        Logger.info(format("Created druid-{node_type_lowercase} jvm.config"))

    # All druid nodes have dependency on hdfs_client
    ensure_hadoop_directories()
    download_database_connector_if_needed()
    # Pull all required dependencies
    pulldeps()


def mutable_config_dict(config):
    rv = {}
    for key, value in config.iteritems():
        rv[key] = value
    return rv


def ensure_hadoop_directories():
    import params
    if 'hdfs-site' not in params.config['configurations']:
        # HDFS Not Installed nothing to do.
        Logger.info("Skipping HDFS directory creation as HDFS not installed")
        return

    druid_common_config = params.config['configurations']['druid-common']
    # final overlord config contains both common and overlord config
    druid_middlemanager_config = params.config['configurations'][
        'druid-middlemanager']

    # If user is using HDFS as deep storage create HDFS Directory for storing segments
    deep_storage = druid_common_config["druid.storage.type"]
    storage_dir = druid_common_config["druid.storage.storageDirectory"]

    if deep_storage == 'hdfs':
        # create the home dir for druid
        params.HdfsResource(
            format("/user/{params.druid_user}"),
            type="directory",
            action="create_on_execute",
            owner=params.druid_user,
            recursive_chown=True,
            recursive_chmod=True)

        # create the segment storage dir
        create_hadoop_directory(storage_dir)

    # Create HadoopIndexTask hadoopWorkingPath
    hadoop_working_path = druid_middlemanager_config[
        'druid.indexer.task.hadoopWorkingPath']
    if hadoop_working_path is not None:
        create_hadoop_directory(hadoop_working_path)

    # If HDFS is used for storing logs, create Index Task log directory
    indexer_logs_type = druid_common_config['druid.indexer.logs.type']
    indexer_logs_directory = druid_common_config[
        'druid.indexer.logs.directory']
    if indexer_logs_type == 'hdfs' and indexer_logs_directory is not None:
        create_hadoop_directory(indexer_logs_directory)


def create_hadoop_directory(hadoop_dir):
    import params
    params.HdfsResource(
        hadoop_dir,
        type="directory",
        action="create_on_execute",
        owner=params.druid_user,
        mode=0755)
    Logger.info(format("Created Hadoop Directory [{hadoop_dir}]"))


def ensure_base_directories():
    import params
    Directory(
        [params.druid_log_dir, params.druid_pid_dir],
        mode=0755,
        owner=params.druid_user,
        group=params.user_group,
        create_parents=True,
        recursive_ownership=True, )

    Directory(
        [params.druid_conf_dir, params.druid_common_conf_dir,
         params.druid_coordinator_conf_dir, params.druid_broker_conf_dir,
         params.druid_middlemanager_conf_dir, params.druid_historical_conf_dir,
         params.druid_overlord_conf_dir, params.druid_router_conf_dir,
         params.druid_segment_infoDir, params.druid_tasks_dir],
        mode=0700,
        cd_access='a',
        owner=params.druid_user,
        group=params.user_group,
        create_parents=True,
        recursive_ownership=True, )

    segment_cache_locations = json.loads(params.druid_segment_cache_locations)
    for segment_cache_location in segment_cache_locations:
        Directory(
            segment_cache_location["path"],
            mode=0700,
            owner=params.druid_user,
            group=params.user_group,
            create_parents=True,
            recursive_ownership=True,
            cd_access='a')


def get_daemon_cmd(params=None, node_type=None, command=None):
    return format(
        'source {params.druid_conf_dir}/druid-env.sh ; {params.druid_home}/bin/node.sh {node_type} {command}')


def getPid(params=None, nodeType=None):
    return format('{params.druid_pid_dir}/{nodeType}.pid')


def pulldeps():
    import params
    extensions_list = eval(params.druid_extensions)
    extensions_string = '{0}'.format("-c ".join(extensions_list))
    repository_list = eval(params.druid_repo_list)
    repository_string = '{0}'.format("-r ".join(repository_list))
    if len(extensions_list) > 0:
        try:
            # Make sure druid user has permissions to write dependencies
            Directory(
                [params.druid_extensions_dir,
                 params.druid_hadoop_dependencies_dir],
                mode=0755,
                cd_access='a',
                owner=params.druid_user,
                group=params.user_group,
                create_parents=True,
                recursive_ownership=True, )
            pull_deps_command = format(
                "source {params.druid_conf_dir}/druid-env.sh ; java -classpath '{params.druid_home}/lib/*' -Ddruid.extensions.loadList=[] "
                "-Ddruid.extensions.directory={params.druid_extensions_dir} -Ddruid.extensions.hadoopDependenciesDir={params.druid_hadoop_dependencies_dir} "
                "io.druid.cli.Main tools pull-deps -c {extensions_string} --no-default-hadoop")

            if len(repository_list) > 0:
                pull_deps_command = format(
                    "{pull_deps_command} -r {repository_string}")

            Execute(pull_deps_command, user=params.druid_user)
            Logger.info(format("Pull Dependencies Complete"))
        except:
            show_logs(params.druid_log_dir, params.druid_user)
            raise


def download_database_connector_if_needed():
    """
  Downloads the database connector to use when connecting to the metadata storage
  """
    import params
    if params.metadata_storage_type != 'mysql' or not params.jdbc_driver_jar:
        return

    File(
        params.check_db_connection_jar,
        content=DownloadSource(
            format("http://yum.example.com/hadoop/{check_db_connection_jar_name}")))

    target_jar_with_directory = params.connector_download_dir + os.path.sep + params.jdbc_driver_jar

    if not os.path.exists(target_jar_with_directory):
        File(
            params.downloaded_custom_connector,
            content=DownloadSource(params.connector_curl_source))

        Execute(
            ('cp', '-rf', params.downloaded_custom_connector,
             target_jar_with_directory),
            path=["/bin", "/usr/bin/"],
            sudo=True)

        File(
            target_jar_with_directory,
            owner=params.druid_user,
            group=params.user_group)
