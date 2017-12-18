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
from resource_management.libraries.functions import format
from resource_management.libraries.functions.default import default
from resource_management.libraries.functions import get_kinit_path
from resource_management.libraries.script.script import Script
SERVER_ROLE_DIRECTORY_MAP = {
  'FALCON_SERVER' : 'falcon-server',
  'FALCON_CLIENT' : 'falcon-client'
}

config = Script.get_config()
stack_root = '/opt'


falcon_pid_dir = config['configurations']['falcon-env']['falcon_pid_dir']
server_pid_file = format('{falcon_pid_dir}/falcon.pid')

hadoop_conf_dir = '/etc/hadoop'

falcon_conf_dir = "/etc/falcon"

# Security related/required params
hostname = config['hostname']
security_enabled = config['configurations']['cluster-env']['security_enabled']
kinit_path_local = get_kinit_path(default('/configurations/kerberos-env/executable_search_paths', None))
tmp_dir = Script.get_tmp_dir()
hdfs_user = config['configurations']['hadoop-env']['hdfs_user']
falcon_user = config['configurations']['falcon-env']['falcon_user']
  
stack_name = default("/hostLevelParams/stack_name", None)
