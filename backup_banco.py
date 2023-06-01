import shutil
import datetime

# Caminho do arquivo de banco de dados SQLite3 original
database_file = r'C:\Users\monitoracaolisto\Desktop\e-commerce-website\db.sqlite3'

# Diretório de destino para o backup
backup_directory = r'C:\Users\monitoracaolisto\Desktop\e-commerce-website\bkp_banco\bkp'
backup_directory2 = r'C:\bkp_banco_site\bkp'

# Gera um nome de arquivo com base na data e hora atual
backup_filename = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + '.db'

# Caminho completo do arquivo de backup
backup_path = backup_directory + backup_filename
backup_path2 = backup_directory2 + backup_filename

# Copia o arquivo do banco de dados para o diretório de backup
shutil.copy2(database_file, backup_path)
shutil.copy2(database_file, backup_path2)

print('Backup concluído:', backup_path, backup_path2)
