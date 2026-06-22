# Requisitos previos
Asegúrate de tener instalado lo siguiente en tu sistema local antes de comenzar:
* Python 3.x
* Git

# Pasos para la instalación y ejecución
Sigue estos pasos para clonar el repositorio y levantar el entorno de desarrollo local.

## 1. Clonar el repositorio
Abre tu terminal en la carpeta en la que desees clonar el repositorio e introduce estos comandos
~~~
git clone https://github.com/lizeth-contrerass/Golarin.git
cd Golarin
~~~

## 2. Crear el entorno virtual
Crea un entorno virtual llamado "venv" ejecutando:
~~~
python -m venv venv
~~~

## 3. Activar el entorno virtual
Dependiendo de tu terminal en Windows, el comando de activación varía ligeramente, pero por lo general es este:
~~~
venv\Scripts\activate
~~~
Sabras que el comando habrá funcionado porque verás (venv) al inicio de la línea de tu terminal.
## 4. Instalar las dependencias
Con el entorno virtual activado, instala todas las librerías necesarias (incluyendo Django) desde el archivo de requerimientos:
~~~
pip install -r requirements.txt
~~~
## 5. Aplicar las migraciones de la base de datos
Antes de correr el proyecto por primera vez, necesitas preparar la base de datos local:
~~~
python manage.py migrate
~~~
## 6. Ejecutar el servidor de desarrollo
Finalmente, levanta el servidor local:
~~~
python manage.py runserver
~~~

### Notas adicionales
Si instalas una nueva librería, recuerda actualizar la lista de dependencias:
~~~
pip freeze > requirements.txt
~~~
Tras realizar un git pull, procura volver a ejecutar los siguientes comandos antes de ``python manage.py runserver`` para evitar fallos:
~~~
python manage.py makemigrations
python manage.py migrate
~~~