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

import sys
from resource_management.libraries.script.script import Script
from resource_management.core.exceptions import ClientComponentHasNoStatus

from zookeeper import zookeeper, install_zookeeper


class ZookeeperClient(Script):
    def configure(self, env):
        import params
        env.set_params(params)
        zookeeper(type='client')
        pass

    def start(self, env, upgrade_type=None):
        import params
        env.set_params(params)
        install_zookeeper(first=True)
        self.configure(env)

    def stop(self, env, upgrade_type=None):
        import params
        env.set_params(params)

    def status(self, env):
        raise ClientComponentHasNoStatus()

    def get_component_name(self):
        return "zookeeper-client"

    def install(self, env):
        install_zookeeper()
        self.configure(env)

    def pre_upgrade_restart(self, env, upgrade_type=None):
        print 'todo'


if __name__ == "__main__":
    ZookeeperClient().execute()
