#!/usr/bin/env python
# Author: ailiesiu@cisco.com
# Date: 12/10/2015

"""
A Python script for power cycling a virtual machine.
"""

import atexit
#import argparse
#import getpass
import sys
import textwrap
import time
import socket

from pyVim import connect
from pyVmomi import vim

from flask import Flask, jsonify, Request
from flask_restful import reqparse, abort, Api, Resource


app = Flask(__name__)
api = Api(app)
s           = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(('google.com', 0))
HOST       = s.getsockname()[0]
PORT       = 80
print (HOST, ':', PORT)

#class RestartVM():
class RestartVM(Resource):
    def __init__(self):
        self.args = {}
        print ("Starting")

        self.default_args = {'host' : 'x.x.x.x', 'port' : '443', 'user' : 'root', 'password': 'password', 'type' : 'restart'}

        self.parser = reqparse.RequestParser()
        self.parser.add_argument('name', type=str)     #
        self.parser.add_argument('host', type=str)     #
        self.parser.add_argument('port', type=str)     #
        self.parser.add_argument('user', type=str)     #
        self.parser.add_argument('password', type=str)     #
        self.parser.add_argument('type', type=str)

        self.args = self.parser.parse_args()
        #self.args = self.default_args

        #clean up data set andprovide defaults if needed
        for k, v in self.args.iteritems():
            if v is None  :
                self.args[k] = self.default_args[k]
        print ("new ARGS =", self.args)
        # form a connection...
        self.si = connect.SmartConnect(host=self.args['host'], user=self.args['user'], pwd=self.args['password'], port=self.args['port'])
        atexit.register(connect.Disconnect, self.si)

    def _test(self):
        #TODO
        pass

    def post(self):
        vm = self._getVM()
        r = {}

        if self.args['type'] == 'restart' or self.args['type'] == 'stop':
            r['start'] = self._stopVM(vm)

        if self.args['type'] == 'restart' or self.args['type'] == 'start' :
            r['stop'] = self._startVM(vm)

        return r, 201

    def _stopVM(self, vm):
        print ('Running _rstartVM')
        if vm.runtime.powerState == vim.VirtualMachinePowerState.poweredOn:
            # using time.sleep we just wait until the power off action
            # is complete.
            print ("powering off...")
            task = vm.PowerOff()
            while task.info.state not in [vim.TaskInfo.State.success,
                                          vim.TaskInfo.State.error]:
                time.sleep(1)
            print ("power is off.")

        return {'power down result' : 'done'}

    def _startVM(self, vm):
        print ("powering on VM %s") % vm.name
        if vm.runtime.powerState != vim.VirtualMachinePowerState.poweredOn:

            task = vm.PowerOn()

            answers = {}
            while task.info.state not in [vim.TaskInfo.State.success,
                                          vim.TaskInfo.State.error]:

                if vm.runtime.question is not None:
                    question_id = vm.runtime.question.id
                    if question_id not in answers.keys():
                        answers[question_id] = self._answer_vm_question(vm)
                        vm.AnswerVM(question_id, answers[question_id])

            if task.info.state == vim.TaskInfo.State.error:
                # some vSphere errors only come with their class and no other message
                print ("error type: %s") % task.info.error.__class__.__name__
                print ("found cause: %s") % task.info.error.faultCause
                for fault_msg in task.info.error.faultMessage:
                    print (fault_msg.key)
                    print (fault_msg.message)
                return ({'Power on result' : 'woops'})
            else:
                return ({'Power on result' : 'Powered Up'})

    def _getVM(self):
        # search the whole inventory tree recursively
        vm = None
        entity_stack = self.si.content.rootFolder.childEntity

        while entity_stack:
            entity = entity_stack.pop()

            if entity.name == self.args['name']:
                vm = entity
                del entity_stack[0:len(entity_stack)]
            elif hasattr(entity, 'childEntity'):
                entity_stack.extend(entity.childEntity)
            elif isinstance(entity, vim.Datacenter):
                entity_stack.append(entity.vmFolder)

        if not isinstance(vm, vim.VirtualMachine):
            print ("could not find a virtual machine with the name %s" )% self.args.name
            sys.exit(-1)

        print ("Found VirtualMachine: %s Name: %s") % (vm, vm.name)
        return vm

    def _answer_vm_question(virtual_machine):
        print "\n"
        choices = virtual_machine.runtime.question.choice.choiceInfo
        default_option = None
        if virtual_machine.runtime.question.choice.defaultIndex is not None:
            ii = virtual_machine.runtime.question.choice.defaultIndex
            default_option = choices[ii]
        choice = None
        while choice not in [o.key for o in choices]:
            print "VM power on is paused by this question:\n\n"
            print "\n".join(textwrap.wrap(
                virtual_machine.runtime.question.text, 60))
            for option in choices:
                print "\t %s: %s " % (option.key, option.label)
            if default_option is not None:
                print "default (%s): %s\n" % (default_option.label,
                                              default_option.key)
            choice = raw_input("\nchoice number: ").strip()
            print "..."
        return choice

api.add_resource(RestartVM, '/restartVM')


if __name__ == '__main__':
    app.run(debug=True,  host=HOST, port=PORT)
    #v= RestartVM()
