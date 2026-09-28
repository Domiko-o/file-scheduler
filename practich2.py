import os
import shutil
import zipfile
import schedule
import time
import logging
import argparse
import json


class Logger:

    def __init__(self, log_file="scheduler.log"):
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            encoding="utf-8"
        )
        self.logger = logging.getLogger(__name__)

    def log(self, message):
        self.logger.info(message)
        print(message)


class FileOperations:

    @staticmethod
    def copy_file(src, dst):
        shutil.copy2(src, dst)

    @staticmethod
    def move_file(src, dst):
        shutil.move(src, dst)

    @staticmethod
    def delete_file(src):
        if os.path.isfile(src):
            os.remove(src)
        else:
            shutil.rmtree(src)

    @staticmethod
    def archive_file(src, dst):
        with zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED) as zipf:
            if os.path.isfile(src):
                zipf.write(src, os.path.basename(src))
            else:
                for root, dirs, files in os.walk(src):
                    for file in files:
                        zipf.write(os.path.join(root, file),
                                   os.path.relpath(os.path.join(root, file),
                                                   os.path.join(src, '..')))


class Task:

    def __init__(self, task_id, operation, source, destination=None, schedule_time=None):
        self.task_id = task_id
        self.operation = operation
        self.source = source
        self.destination = destination
        self.schedule_time = schedule_time

    def __repr__(self):
        return f"[ID:{self.task_id}] {self.operation.upper()} | {self.source} -> {self.destination} | Расписание: {self.schedule_time}"


class Scheduler:

    def __init__(self, logger):
        self.tasks = []
        self.next_id = 1
        self.logger = logger
        self.file_ops = FileOperations()
        self.load_tasks()

    def add_task(self, operation, source, destination, schedule_time):
        task = Task(self.next_id, operation, source, destination, schedule_time)
        self.tasks.append(task)

        if schedule_time and "daily" in schedule_time:
            time_str = ":".join(schedule_time.split(':')[1:])
            schedule.every().day.at(time_str).do(self.run_task, task)

        self.next_id += 1
        self.save_tasks()
        self.logger.log(f"Добавлена задача: {task}")

    def remove_task(self, task_id):
        self.tasks = [t for t in self.tasks if t.task_id != task_id]
        self.save_tasks()
        self.logger.log(f"Задача {task_id} удалена.")

    def view_tasks(self):
        if not self.tasks:
            print("Список задач пуст.")
        else:
            print("\n--- Запланированные задачи ---")
            for task in self.tasks:
                print(task)
            print("-----------------------------\n")

    def run_task(self, task):
        try:
            if task.operation == 'copy':
                self.file_ops.copy_file(task.source, task.destination)
            elif task.operation == 'move':
                self.file_ops.move_file(task.source, task.destination)
            elif task.operation == 'delete':
                self.file_ops.delete_file(task.source)
            elif task.operation == 'archive':
                self.file_ops.archive_file(task.source, task.destination)
            else:
                raise ValueError("Неизвестная операция")

            self.logger.log(f"Задача ID {task.task_id} ({task.operation}): Успешно")
        except Exception as e:
            self.logger.log(f"Задача ID {task.task_id} ({task.operation}): Ошибка - {str(e)}")

    def save_tasks(self):
        with open('tasks.json', 'w', encoding='utf-8') as f:
            json.dump([t.__dict__ for t in self.tasks], f, ensure_ascii=False, indent=4)

    def load_tasks(self):
        if os.path.exists('tasks.json'):
            with open('tasks.json', 'r', encoding='utf-8') as f:
                tasks_data = json.load(f)
                for data in tasks_data:
                    task = Task(**data)
                    self.tasks.append(task)
                    if self.next_id <= task.task_id:
                        self.next_id = task.task_id + 1
                    if task.schedule_time and "daily" in task.schedule_time:
                        time_str = ":".join(task.schedule_time.split(':')[1:])
                        schedule.every().day.at(time_str).do(self.run_task, task)

    def start(self):
        self.logger.log("Шедулер запущен. Нажмите Ctrl+C для остановки.")
        try:
            while True:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.log("\nШедулер остановлен пользователем.")


def main():
    logger = Logger()
    scheduler = Scheduler(logger)

    parser = argparse.ArgumentParser(description="Файловый шедулер (МДК.01.04)")
    parser.add_argument("command", choices=['add', 'view', 'delete', 'start'], help="Команда")
    parser.add_argument("--op", choices=['copy', 'move', 'delete', 'archive'], help="Операция")
    parser.add_argument("--src", help="Путь к исходному файлу/папке")
    parser.add_argument("--dst", help="Путь назначения")
    parser.add_argument("--time", help="Расписание (например, daily:15:30)")
    parser.add_argument("--id", type=int, help="ID задачи для удаления")

    args = parser.parse_args()

    if args.command == 'add':
        if not args.op or not args.src:
            print("Ошибка: укажите --op и --src")
            return
        dst = args.dst if args.dst else ""
        scheduler.add_task(args.op, args.src, dst, args.time)

    elif args.command == 'view':
        scheduler.view_tasks()

    elif args.command == 'delete':
        if not args.id:
            print("Ошибка: укажите --id")
            return
        scheduler.remove_task(args.id)

    elif args.command == 'start':
        scheduler.start()


if __name__ == "__main__":
    main()