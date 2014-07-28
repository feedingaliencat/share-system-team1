#!/usr/bin/env python
#-*- coding: utf-8 -*-

from colorMessage import Message
import ConfigParser
import platform
import getpass
import cmd
import re
import os

# local imports
from communication_system import CmdMessageClient


FILE_CONFIG = "config.ini"


def ask_for_email():
    email_regex = re.compile('[^@]+@[^@]+\.[^@]+')
    while True:
        email = raw_input('insert your user email: ')
        if email_regex.match(email):
            break
        else:
            Message('WARNING', 'invalid email')


class RawBoxExecuter(object):

    def __init__(self, comm_sock):
        self.comm_sock = comm_sock

    def _create_user(self, username=None):
        """ Create user if not exists """
        # username
        if not username:
            username = ask_for_email()

        # password
        while True:
            password = getpass.getpass('insert your password: ')
            rpt_password = getpass.getpass('Repeat your password: ')
            if password == rpt_password:
                break
            else:
                Message('WARNING', 'password not matched')

        # send collected informations
        param = {
            'user': username,
            'psw': password
        }
        self.comm_sock.send_message("create_user", param)
        self.print_response(self.comm_sock.read_message())

    def _activate_user(self, username=None, code=None):
        """ activate user previously created """
        if not username:
            username = ask_for_email()

        # code
        while not code:
            code = raw_input("insert your code: ")
            if len(code) != 32:
                Message('WARNING', 'invalid code must be 32 character')
                code = None

        # send collected informations
        param = {
            'user': username,
            'code': code
        }
        self.comm_sock.send_message("activate_user", param)
        self.print_response(self.comm_sock.read_message())

    def _delete_user(self, username=None):
        """ delete user if is logged """
        if not username:
            username = ask_for_email()

        param = {
            'user': username
        }
        self.comm_sock.send_message("delete_user", param)
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

    def error(self, message=None):
        if message:
            print message
        else:
            print "hum... unknown command, please type help"

    def do_create(self, line):
        """
        create a new RawBox user
        create user <email>
        """
        try:
            command = line.split()[0]
            arguments = line.split()[1]
            if command != 'user':
                self.error("error, wrong command. Use 'create user'")
            else:
                self.executer._create_user(arguments)
        except IndexError:
            self.error("error, must use command user")
            Message('INFO', self.do_create.__doc__)

    def do_activate(self, line):
        """
        activate a new RawBox user previously created
        activate <email> <code>
        """
        user = None
        try:
            user = line.split()[0]
            code = line.split()[1]
            self.executer._activate_user(user, code)
        except IndexError:
            if not user:
                Message('INFO', self.do_activate.__doc__)
            else:
                self.error(
                    "You have to specify: <your email> <your activation code>"
                )

    def do_delete(self, line):
        """
        delete a RawBox user if He is logged
        """
        if line:
            user = line.split()[0]
            self.executer._delete_user(user)
        else:
            Message('INFO', self.do_delete.__doc__)

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

    config = ConfigParser.ConfigParser()
    config.read(FILE_CONFIG)
    host = config.get('cmd', 'host')
    port = config.get('cmd', 'port')
    comm_sock = CmdMessageClient(host, int(port))
    try:
        executer = RawBoxExecuter(comm_sock)
        RawBoxCmd(executer).cmdloop()
    except KeyboardInterrupt:
        print "[exit]"

if __name__ == '__main__':
    main()
