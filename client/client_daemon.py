#!/usr/bin/env python
#-*- coding: utf-8 -*-


# inotify observer unable to detect 'dragging file to trash' events
# from https://github.com/gorakhargosh/watchdog/issues/46 use polling solution

# from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver as Observer
from watchdog.events import FileSystemEventHandler
from requests.auth import HTTPBasicAuth
import requests
import hashlib
import shutil
import base64
import time
import json
import os


SERVER_URL = "localhost"
SERVER_PORT = "5000"
API_PREFIX = "API/v1"


class ServerCommunicator(object):

    def __init__(self, server_url, username, password, dir_path, snapshot_manager):
        self.auth = HTTPBasicAuth(username, password)
        self.server_url = server_url
        self.dir_path = dir_path
        self.snapshot_manager = snapshot_manager

    def setExecuter(self, executer):
        self.executer = executer

    def _try_request(self, callback, success = '', error = '',retry_delay = 2, *args, **kwargs):
        """ try a request until it's a success """
        while True:
            try:
                request_result = callback(
                    auth=self.auth,
                    *args, **kwargs)
                if request_result.status_code == 401:
                    print "user not logged"
                else:
                    print success
                return request_result
            except requests.exceptions.RequestException:
                time.sleep(retry_delay)
                print error

    def synchronize(self, operation_handler, snapshot_manager):
        """Synchronize client and server"""

        server_url = "{}/files/".format(self.server_url)
        request = {"url": server_url}
        sync = self._try_request(requests.get, "getFile success", "getFile fail", **request)
        
        if sync.status_code != 401:
            server_snapshot = sync.json()['snapshot']
            server_timestamp =sync.json()['timestamp']
            print "SERVER SAY: ", server_snapshot, server_timestamp ,"\n"
            command_list = snapshot_manager.syncronize_dispatcher(server_timestamp, server_snapshot)
            self.executer.syncronize_executer(command_list)
            snapshot_manager.save_snapshot(server_timestamp)

    def get_relpath(self, abs_path):
        """form absolute path return relative path """
        if abs_path.startswith(self.dir_path):
            return abs_path[len(self.dir_path) + 1:]
        return abs_path

    def get_abspath(self, dst_path):
        """ from relative path return absolute path """
        return os.path.join(self.dir_path, dst_path)

    def get_url_relpath(self, abs_path):
        """ form get_abspath return the relative path for url """
        return self.get_relpath(abs_path).replace(os.path.sep, '/')

    def download_file(self, dst_path):
        """ download a file from server"""

        error_log = "ERROR on download request " + dst_path
        success_log = "file downloaded! " + dst_path

        server_url = "{}/files/{}".format(
            self.server_url,
            self.get_url_relpath(dst_path))

        request = {"url": server_url}
        
        r = self._try_request(requests.get, success_log, error_log, **request)
        local_path = self.get_abspath(dst_path)
        
        if r.status_code == 200:
            return local_path, r.text
        elif r.status_code == 401 or r.status_code == 404:
            return False, False

    def upload_file(self, dst_path, put_file = False):
        """ upload a file to server """

        file_content = ''
        try:
            file_content = open(dst_path, 'rb')
        except IOError:
            return False  # Atomic create and delete error!

        server_url = "{}/files/{}".format(
            self.server_url,
            self.get_url_relpath(dst_path))

        error_log = "ERROR upload request " + dst_path
        success_log = "file uploaded! " + dst_path
        request = {
            "url": server_url,
            "files": {'file_content': file_content}
        }
        
        if put_file:
            r = self._try_request(requests.put, success_log, error_log, **request)
        else:
            r = self._try_request(requests.post, success_log, error_log, **request)
        if r.status_code == 409:
            print "already exists"
        elif r.status_code == 201:
            self.snapshot_manager.save_snapshot(r.text)

    def delete_file(self, dst_path):
        """ send to server a message of file delete """

        error_log = "ERROR delete request " + dst_path
        success_log = "file deleted! " + dst_path

        server_url = "{}/actions/delete".format(self.server_url)
        request = {
            "url": server_url,
            "data": {"path": self.get_url_relpath(dst_path)}
        }
        r = self._try_request(requests.post, success_log, error_log, **request)
        if r.status_code == 404:
            print "file not found on server"
        elif r.status_code == 201:
            self.snapshot_manager.save_snapshot(r.text)

    def move_file(self, src_path, dst_path):
        """ send to server a message of file moved """
        
        error_log = "ERROR move request " + dst_path
        success_log = "file moved! " + dst_path

        server_url = "{}/actions/move".format(self.server_url)
        src_path = self.get_url_relpath(src_path)
        dst_path = self.get_url_relpath(dst_path)

        request = {
            "url": server_url,
            "data": {"file_src": src_path, "file_dest": dst_path}
        }
        
        r = self._try_request(requests.post, success_log, error_log, **request)
        if r.status_code == 404:
            print "file not found on server"
        elif r.status_code == 201:
            self.snapshot_manager.save_snapshot(r.text)

    def copy_file(self, src_path, dst_path):
        """ send to server a message of copy file"""

        error_log = "ERROR copy request " + dst_path
        success_log = "file copied! " + dst_path

        server_url = "{}/actions/copy".format(self.server_url)
        src_path = self.get_url_relpath(src_path)
        dst_path = self.get_url_relpath(dst_path)

        request = {
            "url": server_url,
            "data": {"file_src": src_path, "file_dest": dst_path}
        }
        r = self._try_request(requests.post, success_log, error_log, **request)
        if r.status_code == 404:
            print "file not found on server"
        elif r.status_code == 201:
            self.snapshot_manager.save_snapshot(r.text)

    def create_user(self, username, password):
        
        error_log = "User creation error"
        success_log = "user created!"

        server_url = "{}/create_user".format(self.server_url)

        request = {
            "url": server_url,
            "data": {
                "user": username,
                "psw": password
            }
        }

        response = self._try_request(requests.post, success_log, error_log, **request).status_code
        if response == 201:
            print "created!"
        elif response == 409:
            print "user already exists"
        else:
            print "bad request"


class FileSystemOperator(object):

    def __init__(self, event_handler, server_com):
        self.event_handler = event_handler
        self.server_com = server_com

    def send_lock(self, path):
        self.event_handler.path_ignored.append(path)

    def send_unlock(self):
        self.event_handler.path_ignored = []

    def write_a_file(self, path):
        """
        write a file (download if exist or not [get and put])

            send lock to watchdog
            download the file from server
            create directory chain
            create file
            send unlock to watchdog
        """

        self.send_lock(self.server_com.get_abspath(path))
        abs_path, content = self.server_com.download_file(path)
        if abs_path and content:
            try:
                os.makedirs(os.path.split(abs_path)[0], 0755 )
            except OSError:
                pass
            with open(abs_path, 'w') as f:
                f.write(content)
            time.sleep(3)
        else:
            print "file not found on server"
        self.send_unlock()

    def move_a_file(self, origin_path, dst_path):
        """
        move a file

            send lock to watchdog for origin and dst path
            create directory chain for dst_path
            move the file from origin_path to dst_path
            send unlock to watchdog
        """
        self.send_lock(self.server_com.get_abspath(origin_path))
        self.send_lock(self.server_com.get_abspath(dst_path))
        try:
            os.makedirs(os.path.split(dst_path)[0], 0755)
        except OSError:
            pass
        shutil.move(origin_path, dst_path)
        self.send_unlock()

    def copy_a_file(self, origin_path, dst_path):
        """
        copy a file

            send lock to watchdog for origin and dest path
            create directory chain for dst_path
            copy the file from origin_path to dst_path
            send unlock to watchdog
        """
        self.send_lock(self.server_com.get_abspath(origin_path))
        self.send_lock(self.server_com.get_abspath(dst_path))
        try:
            os.makedirs(os.path.split(dst_path)[0], 0755)
        except OSError:
            pass
        shutil.copyfile(origin_path, dst_path)
        self.send_unlock()

    def delete_a_file(self, path):
        """
        delete a file

            send lock to watchdog
            delete file
            send unlock to watchdog
        """
        self.send_lock(self.server_com.get_abspath(path))
        if os.path.isdir(path):
            try:
                shutil.rmtree(path)
            except IOError:
                pass
        else:
            os.remove(path)
        self.send_unlock()


def load_config():
    try:
        with open('config.json', 'r') as config_file:
            config = json.load(config_file)
        return config
    except IOError:
        dir_path = os.path.join(os.path.expanduser("~"), "RawBox")
        try:
            os.makedirs(dir_path)
        except OSError:
            pass
            
        # TODO: ask to cmd_manager to create a new user
        user = "Alalah@tropos.fo"
        psw = "pokpsd"

        config = {
            "server_url" : "http://{}:{}/{}".format(
                SERVER_URL,
                SERVER_PORT,
                API_PREFIX
            ),
            "dir_path": dir_path,
            "snapshot_file_path": None,
            "cmd_host": "localhost",
            "cmd_port": "6666",
            "username": user,
            "password": psw 
        }
        with open('config.json', 'w') as config_file:
            json.dump(config, config_file)
        return config


class DirectoryEventHandler(FileSystemEventHandler):

    def __init__(self, cmd, snap):
        self.cmd = cmd
        self.snap = snap
        self.path_ignored = []
        
    def _is_copy(self, abs_path):
        """
        check if a file_md5 already exists in my local snapshot
        IF IS A COPY : return the first path of already exists file
        ELSE: return False
        """
        file_md5 = self.snap.file_snapMd5(abs_path)
        if not file_md5:
            return False
        if file_md5 in self.snap.local_full_snapshot:
            return self.snap.local_full_snapshot[file_md5][0]
        return False

    def on_moved(self, event):
        """Called when a file or a directory is moved or renamed.

        :param event:
            Event representing file/directory movement.
        :type event:
            :class:`DirMovedEvent` or :class:`FileMovedEvent`
        """
        if event.src_path not in self.path_ignored:
            if not event.is_directory:
                self.cmd.move_file(event.src_path, event.dest_path)
        else:
            print "ingnored move on ", event.src_path

    def on_created(self, event):
        """Called when a file or directory is created.

        :param event:
            Event representing file/directory creation.
        :type event:
            :class:`DirCreatedEvent` or :class:`FileCreatedEvent`
        """
       
        if event.src_path not in self.path_ignored:
            copy = self._is_copy(event.src_path)
            if copy:
                self.cmd.copy_file(copy, event.src_path)
            else:
                self.cmd.upload_file(event.src_path)
        else:
            print "ingnored create on ", event.src_path

    def on_deleted(self, event):
        """Called when a file or directory is deleted.

        :param event:
            Event representing file/directory deletion.
        :type event:
            :class:`DirDeletedEvent` or :class:`FileDeletedEvent`
        """
        if event.src_path not in self.path_ignored:
            if not event.is_directory:
                self.cmd.delete_file(event.src_path)
        else:
            print "ingnored deletion on ", event.src_path

    def on_modified(self, event):
        """Called when a file or directory is modified.

        :param event:
            Event representing file/directory modification.
        :type event:
            :class:`DirModifiedEvent` or :class:`FileModifiedEvent`
        """
        
        if event.src_path not in self.path_ignored:
            if not event.is_directory:
                self.cmd.upload_file(event.src_path, put_file=True)
        else:
            print "ingnored modified on ", event.src_path


class DirSnapshotManager(object):
    def __init__(self, dir_path, snapshot_file_path):
        """ load the last global snapshot and create a instant_snapshot of local directory"""
        self.dir_path = dir_path
        self.snapshot_file_path = snapshot_file_path
        self.last_status = self._load_status()
        self.local_full_snapshot = self.instant_snapshot()

    def local_check(self):
        """ check id daemon is synchronized with local directory """
        local_global_snapshot = self.global_md5()
        last_global_snapthot = self.last_status['snapshot']
        return local_global_snapshot == last_global_snapthot

    def is_syncro(self, server_timestamp):
        """ check if daemon timestamp is synchronized with server timestamp"""
        server_timestamp = float(server_timestamp)
        client_timestamp = float(self.last_status['timestamp'])
        return server_timestamp == client_timestamp

    def _load_status(self):
        """ load from file the last snapshot """
        with open(self.snapshot_file_path) as f:
            return json.load(f)

    def file_snapMd5(self, file_path):
        """ calculate the md5 of a file """
        file_md5 = hashlib.md5()
        if os.path.isdir(file_path):
            return False
        with open(file_path, 'rb') as afile:
            buf = afile.read(2048)
            while len(buf) > 0:
                file_md5.update(buf)
                buf = afile.read(2048)
        return file_md5.hexdigest()

    def global_md5(self, server_snapshot = False):
        """ calculate the global md5 of local_full_snapshot """
        if server_snapshot:
            snap_list = list(server_snapshot)
        else:
            snap_list = list(self.local_full_snapshot)
        snap_list.sort()
        return hashlib.md5(str(snap_list)).hexdigest()

    def instant_snapshot(self):
        """ create a snapshot of directory """

        dir_snapshot = {}
        for root, dirs, files in os.walk(self.dir_path):
            for f in files:
                full_path = os.path.join(root, f)
                file_md5 = self.file_snapMd5(full_path)
                rel_path = f
                if file_md5 in dir_snapshot:
                    dir_snapshot[file_md5].append(rel_path)
                else:
                    dir_snapshot[file_md5] = [rel_path]
        return dir_snapshot

    def save_snapshot(self, timestamp):
        """ save snapshot to file """
        self.local_full_snapshot = self.instant_snapshot()
        self.last_status['timestamp'] = timestamp
        self.last_status['snapshot'] = self.global_md5()

        with open(self.snapshot_file_path, 'w') as f:
            f.write(json.dumps({"timestamp": timestamp, "snapshot": self.last_status['snapshot']}))

    def diff_snapshot_paths(self, snap_client, snap_server):
        """
            from 2 snapshot return 3 list of path difference:
            list of new server path
            list of new client path
            list of equal path
        """
        client_paths = [val for subl in snap_client.values() for val in subl]
        server_paths = [val['path'] for subl in snap_server.values() for val in subl]
        new_server_paths = list(set(server_paths) - set(client_paths))
        new_client_paths = list(set(client_paths) - set(server_paths))
        equal_paths = list(set(client_paths).intersection(set(server_paths)))
        
        return new_client_paths, new_server_paths, equal_paths
        
    def find_file_md5(self, snapshot, new_path, is_server = True):
        """ from snapshot and a path find the md5 of file inside snapshot"""
        for md5, paths in snapshot.items():
            for path in paths:
                if is_server:
                    if path['path'] == new_path:
                        return md5
                else:
                     if path == new_path:
                        return md5

    def check_files_timestamp(self, snapshot, new_path):
        paths_timestamps = [val for subl in snapshot.values() for val in subl]
        for path_timestamp in paths_timestamps:
            if path_timestamp['path'] == new_path:
                return path_timestamp['timestamp'] < self.last_status['timestamp']

    def syncronize_dispatcher(self, server_timestamp, server_snapshot):
        """ return the list of command to do """
        new_client_paths, new_server_paths, equal_paths =  self.diff_snapshot_paths(self.local_full_snapshot , server_snapshot)
        command_list = []
        #NO internal conflict
        if self.local_check():  #1)
            if  not self.is_syncro(server_timestamp): #1) b.
                for new_server_path in new_server_paths: #1) b 1
                    if not self.find_file_md5(server_snapshot, new_server_path) in self.local_full_snapshot: #1) b 1 I
                        print "download:\t" + new_server_path
                        command_list.append({new_server_path: 'local_download'}) 
                    else: #1) b 1 II
                        print "copy or rename:\t" + new_server_path
                        command_list.append({new_server_path: 'local_copy'})
                
                for equal_path in equal_paths: #1) b 2
                    if self.find_file_md5(self.local_full_snapshot, equal_path, False) != self.find_file_md5(server_snapshot, equal_path):
                        print "update download:\t" + equal_path
                        command_list.append({equal_path: 'local_download'}) 
                    else:
                        print "no action:\t" + equal_path
                
                for new_client_path in new_client_paths: #1) b 3
                    print "remove local:\t" + new_client_path
                    command_list.append({new_client_path: 'local_delete'}) 
            else:
                print "synchronized"
        #internal conflicts
        else: # 2)
            if self.is_syncro(server_timestamp): #2) a
                print "****\tpush all\t****" 
                for new_server_path in new_server_paths: #2) a 1
                    print "remove:\t" + new_server_path
                    command_list.append({new_server_path: 'remote_delete'}) 
                for equal_path in equal_paths: #2) a 2
                    if self.find_file_md5(self.local_full_snapshot, equal_path, False) != self.find_file_md5(server_snapshot, equal_path):
                        print "update:\t" + equal_path
                        command_list.append({equal_path: 'remote_update'})
                    else:
                        print "no action:\t" + equal_path
                for new_client_path in new_client_paths: #2) a 3
                    print "upload:\t" + new_client_path
                    command_list.append({new_client_path: 'remote_upload'}) 
            
            elif not self.is_syncro(server_timestamp): #2) b
                for new_server_path in new_server_paths: #2) b 1
                    if not self.find_file_md5(server_snapshot, new_server_path) in self.local_full_snapshot: #2) b 1 I
                        if self.check_files_timestamp(server_snapshot, new_server_path):
                            print "delete remote:\t" + new_server_path
                            command_list.append({new_server_path: 'remote_delete'}) 
                        else:
                            print "download local:\t" + new_server_path
                            command_list.append({new_server_path: 'local_download'}) 
                    else: #2) b 1 II
                        print  "copy or rename:\t" + new_server_path
                        command_list.append({new_server_path: 'local_copy'}) #??? 
               
                for equal_path in equal_paths: #2) b 2
                    if self.find_file_md5(self.local_full_snapshot, equal_path, False) != self.find_file_md5(server_snapshot, equal_path):
                        if self.check_files_timestamp(server_snapshot, equal_path): #2) b 2 I
                            print "server push:\t" + equal_path
                            command_list.append({equal_path: 'remote_upload'})
                        else:  #2) b 2 II 
                            print "create.conflicted:\t" + equal_path
                            conflicted_path = "{}/{}.conflicted".format(
                                "/".join(equal_path.split('/')[:-1]),
                                "".join(equal_path.split('/')[-1])
                            )
                            command_list.append({conflicted_path: 'remote_upload'})
                            command_list.append({equal_path: 'local_copy_and_rename:' + conflicted_path})
                    else:
                        print "no action:\t" + equal_path
                for new_client_path in new_client_paths: #2) b 3
                    print "remove remote\t" + new_client_path 
                    command_list.append({new_client_path:'remote_delete'})

        return command_list


class CommandExecuter(object):
    """Execute a list of commands"""
    def __init__(self,file_system_op, server_com):
        self.local = file_system_op
        self.remote = server_com
        
    def syncronize_executer(self, command_list):
        print "EXECUTER\n"
        def error(*args,**kwargs):
            return False

        for command in command_list:
            for path in command:
                command_dest = command[path].split('_')[0]
                command_type = command[path].split('_')[1]
                if command_dest == 'remote':
                    {

                        'delete': self.remote.delete_file,
                    }.get(command_type,error)(path)
                else:
                    {
                        'download': self.local.write_a_file,
                    }.get(command_type,error)(path)


def main():
    config = load_config()
    snapshot_manager = DirSnapshotManager(config['dir_path'], config['snapshot_file_path'])
    
    server_com = ServerCommunicator(
        server_url=config['server_url'],
        username=config['username'],
        password=config['password'],
        dir_path=config['dir_path'],
        snapshot_manager = snapshot_manager)

    event_handler = DirectoryEventHandler(server_com, snapshot_manager)
    file_system_op = FileSystemOperator(event_handler, server_com)
    executer = CommandExecuter(file_system_op, server_com)
    server_com.setExecuter(executer)
    observer = Observer()
    observer.schedule(event_handler, config['dir_path'], recursive=True)

    observer.start()
    try:
        while True:
            server_com.synchronize(file_system_op, snapshot_manager)
            time.sleep(5)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == '__main__':
    main()
