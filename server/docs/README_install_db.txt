======================== setup postgres before the first rawbox server run:
sudo -u postgres psql

postgres=# CREATE DATABASE rawbox;
postgres=# CREATE USER rawbox;
postgres=# \password rawbox
postgres=# \q

...and write the password in your config.ini!

======================== Manage your database (some examples)
sudo -u postgres psql
\list
\c rawbox
\d
\q

SELECT * FROM user;

DROP DATABASE rawbox;
CREATE DATABASE rawbox;
