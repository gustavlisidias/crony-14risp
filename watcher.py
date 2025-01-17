import os
import shutil

from pathlib import Path
from dotenv import load_dotenv

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


load_dotenv(os.path.join(Path(__file__).resolve().parent, '.env'))

source_folder = Path(os.getenv('WATCHER_SRC'))
destination_folder = Path(os.getenv('WATCHER_DST'))


class FileHandler(FileSystemEventHandler):
	def on_created(self, event):
		if event.is_directory:
			relative_path = os.path.relpath(event.src_path, source_folder)
			dest_path = os.path.join(destination_folder, relative_path)
			
			try:
				os.makedirs(dest_path, exist_ok=True)
				print(f'Diretório {relative_path} criado em {destination_folder}')
			except Exception as e:
				print(f'Erro ao criar diretório {relative_path}: {e}')
		else:
			relative_path = os.path.relpath(event.src_path, source_folder)
			dest_path = os.path.join(destination_folder, relative_path)
			
			try:
				os.makedirs(os.path.dirname(dest_path), exist_ok=True)
				shutil.copy2(event.src_path, dest_path)
				print(f'Arquivo {relative_path} copiado para {destination_folder}')
			except Exception as e:
				print(f'Erro ao copiar {relative_path}: {e}')


def start_monitoring():
	event_handler = FileHandler()
	observer = Observer()
	observer.schedule(event_handler, source_folder, recursive=True)
	observer.start()
	
	try:
		while True:
			pass
	except KeyboardInterrupt:
		observer.stop()
	observer.join()


if __name__ == '__main__':
	print(f'Pasta de origem: {source_folder}')
	print(f'Pasta de destino: {destination_folder}')
	start_monitoring()
