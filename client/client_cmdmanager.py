#!/usr/bin/env python
#-*- coding: utf-8 -*-

from colorMessage import Message
import platform
import getpass
import cmd
import re
import os

# internal imports
from communication_system import CmdMessageClient
from client_daemon import load_config


class RawBoxExecuter(object):

    def __init__(self, comm_sock):
        self.comm_sock = comm_sock

    def _create_user(self, username=None):
        """ Create user if not exists """
        # username
        if not username:
            username = raw_input('insert your user name: ')
        else:
            username = " ".join(username)

        # password
        while True:
            password = getpass.getpass('insert your password: ')
            rpt_password = getpass.getpass('Repeat your password: ')
            if password == rpt_password:
                break
            else:
                Message('WARNING', 'password not matched')

        # email
        email_regex = re.compile('[^@]+@[^@]+\.[^@]+')
        while True:
            email = raw_input('insert your user email: ')
            if email_regex.match(email):
                break
            else:
                Message('WARNING', 'invalid email')

        # send collected informations
        param = {
            'user': username,
            'psw': password,
            'email': email
        }
        self.comm_sock.send_message("create_user", param)
        self.print_response(self.comm_sock.read_message())

    def print_response(self, response):
        """ Print response from the daemon.
        the response is a dictionary as:
        {
            'request': type of command
            'body': {
                'result': result for command
                'details': list of eventual detail for command
            }
        }
        """
        print 'Response for "{}" command'.format(response['request'])
        print 'result: {}'.format(response['body']['result'])
        if response['body']['details']:
            print 'details:'
            for detail in response['body']['details']:
                print '\t{}'.format(detail)


class RawBoxCmd(cmd.Cmd):
    """ RawBox command line interface """

    intro = Message().color(
        'INFO',
        (
            "##### Hello guy!... or maybe girl, welcome to RawBox ######\n"
            "type ? to see help\n\n"
        )
    )
    doc_header = Message().color(
        'INFO', "command list, type ? <topic> to see more :)"
    )
    prompt = Message().color('HEADER', '(RawBox) ')
    ruler = Message().color('INFO', '~')

    def __init__(self, executer):
        cmd.Cmd.__init__(self)
        self.executer = executer

    def error(self, *args):
        print "hum... unknown command, please type help"

    def do_create(self, line):
        """
        create user <name>  (create a new RawBox user)
        create group <name> (create a new shareable folder with your friends)
        """
        if line:
            command = line.split()[0]
            arguments = line.split()[1:]
            {
                'user': self.executer._create_user,
                'group': self.executer._create_group,
            }.get(command, self.error)(arguments)
        else:
            Message('INFO', self.do_create.__doc__)

    def do_q(self, line=None):
        """ exit from RawBox"""
        if raw_input('[Exit] are you sure? y/n ') == 'y':
            return True

    def do_quit(self, line=None):
        """ exit from RawBox"""
        if raw_input('[Exit] are you sure? y/n ') == 'y':
            return True


def main():
    if platform.system() == 'Windows':
        os.system('cls')
    else:
        os.system('clear')

    conf, is_new = load_config()
    comm_sock = CmdMessageClient(conf['cmd_host'], conf['cmd_port'])
    try:
        executer = RawBoxExecuter(comm_sock)
        RawBoxCmd(executer).cmdloop()
    except KeyboardInterrupt:
        print "[exit]"

if __name__ == '__main__':
    main()
