#!/usr/bin/env python
#-*- coding: utf-8 -*-

import platform
import getpass
import cmd
import sys
import re
import os

from communication_system import CmdMessageClient
import asyncore
from client_daemon import load_config

sys.path.insert(0, 'utility/')
from colorMessage import Message

def take_input(message, password = False):
    if not  password:
        return raw_input(message)
    else:
        return getpass.getpass(message)

class RawBoxCmd(cmd.Cmd):
    """RawBox command line interface"""

    intro = Message().color('INFO', '##### Hello guy!... or maybe girl, welcome to RawBox ######\ntype ? to see help\n\n')
    doc_header = Message().color('INFO', "command list, type ? <topic> to see more :)")
    prompt = Message().color('HEADER', '(RawBox) ')
    ruler = Message().color('INFO', '~')

    def __init__(self, comm_sock):
        cmd.Cmd.__init__(self)
        self.comm_sock = comm_sock
        
    def _create_user(self, username=None):
        """create user if not exists"""
        command_type = 'create_user'

        if not username:
            username = take_input('insert your user name: ')
        else:
            username = " ".join(username)

        password = take_input('insert your password: ', password = True)
        rpt_password = take_input('Repeat your password: ', password = True)
        while password != rpt_password:
            Message('WARNING', 'password not matched')
            password = take_input('insert your password: ', password = True)
            rpt_password = take_input('Repeat your password: ', password = True)

        email_regex = re.compile('[^@]+@[^@]+\.[^@]+')
        email = take_input('insert your user email: ')
        
        while not email_regex.match(email):
            Message('WARNING', 'invalid email')
            email = take_input('insert your user email: ')

        param = {
                'user': username,
                'psw': password,
                'email': email
            }

        self.comm_sock.send_message(command_type, param)
        self.print_response(self.comm_sock.read_message())

    def _create_group(self, *args):
        """create group/s"""

        command_type = 'create_group'
        param = {'group': args}

        self.comm_sock.send_message(command_type, param)
        self.print_response(self.comm_sock.read_message())

    def _add_user(self, *args):
        """add user/s to a group """
        command_type = 'add_to_group'
        args = args[0]
        users = args[:-1]
        try:
            group = args[-1].split("group=")[1]
            if group.strip() == "":
                raise IndexError
        except IndexError:
            Message('WARNING', '\nyou must specify a group for example add user marco luigi group=your_group')
            return False

        for user in users:
            #call socket message
            print "add user ", user, " to group ", group
            param = {
                'user': user,
                'group': group,
            }
            self.comm_sock.send_message(command_type, param)
            self.print_response(self.comm_sock.read_message())

    def _add_admin(self, *args):
        """add admin/s to a group """
        command_type = 'add_admin'
        param = {'admin': args}

        self.comm_sock.send_message(command_type, param)
        self.print_response(self.comm_sock.read_message())

    def error(self, *args):
        print "hum... unknown command, please type help"

    def do_add(self, line):
        """
    add user <*user_list> group=<group_name> (add a new RawBox user to the group)
    add admin <*user_list> group=<group_name> (add a new RawBox user as admin to the group)
        """
        if line:
            command = line.split()[0]
            arguments = line.split()[1:]
            {
                'user': self._add_user,
                'admin': self._add_admin,
            }.get(command, self.error)(arguments)
        else:
            Message('INFO', self.do_add.__doc__)

    def do_create(self, line):
        """
        create user <name>  (create a new RawBox user)
        create group <name> (create a new shareable folder with your friends)
        """
        if line:
            command = line.split()[0]
            arguments = line.split()[1:]
            {
                'user': self._create_user,
                'group': self._create_group,
            }.get(command, self.error)(arguments)
        else:
            Message('INFO', self.do_create.__doc__)

    def do_q(self, line=None):
        """ exit from RawBox"""
        if take_input('[Exit] are you sure? y/n ') == 'y':
            return True

    def do_quit(self, line=None):
        """ exit from RawBox"""
        if take_input('[Exit] are you sure? y/n ') == 'y':
            return True

    def print_response(self, response):
        print 'Response for "{}" command\nresult: {}'.format(response['request'], response['body'])


def main():
    if platform.system() == 'Windows':
        os.system('cls')
    else:
        os.system('clear')

    conf = load_config()
    comm_sock = CmdMessageClient(conf['cmd_host'], int(conf['cmd_port']))
    try:
        RawBoxCmd(comm_sock).cmdloop()
    except KeyboardInterrupt:
        print "[exit]"

if __name__ == '__main__':
    main()
