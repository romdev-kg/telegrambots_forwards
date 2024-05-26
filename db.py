import sqlite3

class Database:
    def __init__(self, db_file):
        self.connection = sqlite3.connect(db_file)
        self.cursor = self.connection.cursor()

    def user_exists(self, user_id):
        with self.connection:
            result = self.cursor.execute("SELECT * FROM `users` WHERE `user_id` = ?", (user_id,)).fetchmany(1)
            return bool(len(result))

    def add_user(self, user_id):
        with self.connection:
            return self.cursor.execute("INSERT INTO `users` (`user_id`) VALUES (?)", (user_id,))

    def group_exists(self, group_id):
        with self.connection:
            result = self.cursor.execute("SELECT * FROM `groups` WHERE `group_id` = ?", (group_id,)).fetchmany(1)
            return bool(len(result))

    def add_group(self, group_id):
        with self.connection:
            return self.cursor.execute("INSERT INTO `groups` (`group_id`) VALUES (?)", (group_id,))

    def get_users(self):
        with self.connection:
            return self.cursor.execute("SELECT `user_id`, `active` FROM `users`").fetchall()

    def get_groups(self):
        with self.connection:
            return self.cursor.execute("SELECT `group_id`, `active` FROM `groups`").fetchall()

    def set_active(self, entity_id, active, is_user=True):
        with self.connection:
            table = 'users' if is_user else 'groups'
            self.cursor.execute(f"UPDATE `{table}` SET `active` = ? WHERE `{'user_id' if is_user else 'group_id'}` = ?", (active, entity_id))

    def close(self):
        self.connection.close()
