from flask import Flask, jsonify, request, abort, render_template_string, redirect, url_for
import sqlite3
import re

app = Flask(__name__)

# Conectar a la base de datos SQLite
def get_db_connection():
    conn = sqlite3.connect('uniforme_futbol.db')
    conn.row_factory = sqlite3.Row
    return conn

# Crear la tabla de ligas si no existe
def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS ligas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE
        )
    ''')
    conn.commit()
    conn.close()

# Crear una tabla de uniformes para una liga específica
def crear_tabla_uniformes(nombre_liga):
    nombre_tabla = f"uniforme_{re.sub(r'[^a-zA-Z0-9]', '_', nombre_liga.lower())}"
    conn = get_db_connection()
    conn.execute(f'''
        CREATE TABLE IF NOT EXISTS {nombre_tabla} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipo TEXT NOT NULL,
            color_local TEXT NOT NULL,
            color_visitante TEXT NOT NULL
        )
    ''')
    conn.execute(f'''
        CREATE TABLE IF NOT EXISTS {nombre_tabla}_tallas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uniforme_id INTEGER NOT NULL,
            talla TEXT NOT NULL,
            cantidad INTEGER NOT NULL,
            FOREIGN KEY (uniforme_id) REFERENCES {nombre_tabla} (id)
        )
    ''')
    conn.commit()
    conn.close()

# Eliminar una tabla de uniformes y sus tallas
def eliminar_tabla_uniformes(nombre_liga):
    nombre_tabla = f"uniforme_{re.sub(r'[^a-zA-Z0-9]', '_', nombre_liga.lower())}"
    conn = get_db_connection()
    conn.execute(f'DROP TABLE IF EXISTS {nombre_tabla}')
    conn.execute(f'DROP TABLE IF EXISTS {nombre_tabla}_tallas')
    conn.commit()
    conn.close()

# Inicializar la base de datos
init_db()

# Ruta principal para mostrar la lista de ligas
@app.route('/')
def index():
    conn = get_db_connection()
    ligas = conn.execute('SELECT * FROM ligas').fetchall()
    conn.close()
    return render_template_string('''
        <h1>Ligas de Fútbol</h1>
        <h2>Lista de Ligas</h2>
        <ul>
            {% for liga in ligas %}
                <li>
                    {{ liga.nombre }}
                    <a href="/liga/{{ liga.id }}">Ver</a>
                    <a href="/editar_liga/{{ liga.id }}">Editar</a>
                    <form action="/eliminar_liga/{{ liga.id }}" method="POST" style="display:inline;">
                        <button type="submit">Eliminar</button>
                    </form>
                </li>
            {% endfor %}
        </ul>
        <a href="/crear_liga">Crear Nueva Liga</a>
    ''', ligas=ligas)

# Ruta para mostrar los uniformes de una liga específica
@app.route('/liga/<int:id>')
def ver_liga(id):
    conn = get_db_connection()
    liga = conn.execute('SELECT * FROM ligas WHERE id = ?', (id,)).fetchone()
    if liga is None:
        abort(404, description="Liga no encontrada")
    
    nombre_tabla = f"uniforme_{re.sub(r'[^a-zA-Z0-9]', '_', liga['nombre'].lower())}"
    uniformes = conn.execute(f'SELECT * FROM {nombre_tabla}').fetchall()
    uniformes_con_tallas = []
    for unif in uniformes:
        tallas = conn.execute(f'SELECT talla, cantidad FROM {nombre_tabla}_tallas WHERE uniforme_id = ?', (unif['id'],)).fetchall()
        uniformes_con_tallas.append({
            **dict(unif),
            "tallas": [dict(talla) for talla in tallas]
        })
    conn.close()
    return render_template_string('''
        <h1>Uniforme de {{ liga.nombre }}</h1>
        <h2>Lista de Uniformes</h2>
        <ul>
            {% for unif in uniformes %}
                <li>
                    {{ unif.equipo }} - Local: {{ unif.color_local }}, Visitante: {{ unif.color_visitante }}
                    <ul>
                        {% for talla in unif.tallas %}
                            <li>{{ talla.talla }}: {{ talla.cantidad }}</li>
                        {% endfor %}
                    </ul>
                    <a href="/actualizar_uniforme/{{ liga.id }}/{{ unif.id }}">Actualizar</a>
                    <form action="/eliminar_uniforme/{{ liga.id }}/{{ unif.id }}" method="POST" style="display:inline;">
                        <button type="submit">Eliminar</button>
                    </form>
                </li>
            {% endfor %}
        </ul>
        <a href="/agregar_uniforme/{{ liga.id }}">Agregar Nuevo Uniforme</a>
        <a href="/">Volver a la lista de ligas</a>
    ''', liga=liga, uniformes=uniformes_con_tallas)

# Ruta para crear una nueva liga
@app.route('/crear_liga', methods=['GET', 'POST'])
def crear_liga():
    if request.method == 'POST':
        nombre_liga = request.form.get('nombre_liga')
        if not nombre_liga:
            abort(400, description="Nombre de la liga es requerido")
        
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO ligas (nombre) VALUES (?)', (nombre_liga,))
            conn.commit()
            crear_tabla_uniformes(nombre_liga)  # Crear la tabla de uniformes para la nueva liga
        except sqlite3.IntegrityError:
            abort(400, description="La liga ya existe")
        finally:
            conn.close()
        return redirect(url_for('index'))  # Redirige a la página principal
    
    # Mostrar el formulario de creación de liga
    return render_template_string('''
        <h1>Crear Nueva Liga</h1>
        <form method="POST">
            Nombre de la Liga: <input type="text" name="nombre_liga" required><br>
            <button type="submit">Crear</button>
        </form>
        <a href="/">Volver a la lista de ligas</a>
    ''')

# Ruta para editar una liga
@app.route('/editar_liga/<int:id>', methods=['GET', 'POST'])
def editar_liga(id):
    conn = get_db_connection()
    liga = conn.execute('SELECT * FROM ligas WHERE id = ?', (id,)).fetchone()
    if liga is None:
        conn.close()
        abort(404, description="Liga no encontrada")
    
    if request.method == 'POST':
        nuevo_nombre = request.form.get('nombre_liga')
        if not nuevo_nombre:
            abort(400, description="Nombre de la liga es requerido")
        
        # Eliminar las tablas antiguas
        eliminar_tabla_uniformes(liga['nombre'])
        
        # Actualizar el nombre de la liga
        conn.execute('UPDATE ligas SET nombre = ? WHERE id = ?', (nuevo_nombre, id))
        conn.commit()
        
        # Crear nuevas tablas con el nuevo nombre
        crear_tabla_uniformes(nuevo_nombre)
        conn.close()
        return redirect(url_for('index'))  # Redirige a la página principal
    
    # Mostrar el formulario de edición de liga
    conn.close()
    return render_template_string('''
        <h1>Editar Liga</h1>
        <form method="POST">
            Nombre de la Liga: <input type="text" name="nombre_liga" value="{{ liga.nombre }}" required><br>
            <button type="submit">Guardar</button>
        </form>
        <a href="/">Volver a la lista de ligas</a>
    ''', liga=liga)

# Ruta para eliminar una liga
@app.route('/eliminar_liga/<int:id>', methods=['POST'])
def eliminar_liga(id):
    conn = get_db_connection()
    liga = conn.execute('SELECT * FROM ligas WHERE id = ?', (id,)).fetchone()
    if liga is None:
        conn.close()
        abort(404, description="Liga no encontrada")
    
    # Eliminar las tablas de uniformes de la liga
    eliminar_tabla_uniformes(liga['nombre'])
    
    # Eliminar la liga de la tabla de ligas
    conn.execute('DELETE FROM ligas WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))  # Redirige a la página principal

# Ruta para agregar un nuevo uniforme a una liga
@app.route('/agregar_uniforme/<int:liga_id>', methods=['GET', 'POST'])
def agregar_uniforme(liga_id):
    conn = get_db_connection()
    liga = conn.execute('SELECT * FROM ligas WHERE id = ?', (liga_id,)).fetchone()
    if liga is None:
        conn.close()
        abort(404, description="Liga no encontrada")
    
    nombre_tabla = f"uniforme_{re.sub(r'[^a-zA-Z0-9]', '_', liga['nombre'].lower())}"
    
    if request.method == 'POST':
        if not request.form or not 'equipo' in request.form:
            abort(400, description="Datos incompletos")
        
        # Insertar el uniforme en la tabla de la liga
        cursor = conn.cursor()
        cursor.execute(f'''
            INSERT INTO {nombre_tabla} (equipo, color_local, color_visitante)
            VALUES (?, ?, ?)
        ''', (
            request.form['equipo'],
            request.form.get('color_local', ""),
            request.form.get('color_visitante', "")
        ))
        uniforme_id = cursor.lastrowid

        # Insertar las tallas en la tabla de tallas de la liga
        tallas = [
            ("CH", int(request.form.get('cantidad_ch', 0))),
            ("M", int(request.form.get('cantidad_m', 0))),
            ("G", int(request.form.get('cantidad_g', 0)))
        ]
        for talla, cantidad in tallas:
            cursor.execute(f'''
                INSERT INTO {nombre_tabla}_tallas (uniforme_id, talla, cantidad)
                VALUES (?, ?, ?)
            ''', (uniforme_id, talla, cantidad))
        
        conn.commit()
        conn.close()
        return redirect(url_for('ver_liga', id=liga_id))  # Redirige a la página de la liga
    
    # Mostrar el formulario de agregar uniforme
    conn.close()
    return render_template_string('''
        <h1>Agregar Nuevo Uniforme a {{ liga.nombre }}</h1>
        <form method="POST">
            Equipo: <input type="text" name="equipo" required><br>
            Color Local: <input type="text" name="color_local"><br>
            Color Visitante: <input type="text" name="color_visitante"><br>
            Talla CH: <input type="number" name="cantidad_ch"><br>
            Talla M: <input type="number" name="cantidad_m"><br>
            Talla G: <input type="number" name="cantidad_g"><br>
            <button type="submit">Agregar</button>
        </form>
        <a href="/liga/{{ liga.id }}">Volver a la lista de uniformes</a>
    ''', liga=liga)

# Ruta para actualizar un uniforme de una liga
@app.route('/actualizar_uniforme/<int:liga_id>/<int:uniforme_id>', methods=['GET', 'POST'])
def actualizar_uniforme(liga_id, uniforme_id):
    conn = get_db_connection()
    liga = conn.execute('SELECT * FROM ligas WHERE id = ?', (liga_id,)).fetchone()
    if liga is None:
        conn.close()
        abort(404, description="Liga no encontrada")
    
    nombre_tabla = f"uniforme_{re.sub(r'[^a-zA-Z0-9]', '_', liga['nombre'].lower())}"
    uniforme = conn.execute(f'SELECT * FROM {nombre_tabla} WHERE id = ?', (uniforme_id,)).fetchone()
    if uniforme is None:
        conn.close()
        abort(404, description="Uniforme no encontrado")
    
    tallas = conn.execute(f'SELECT talla, cantidad FROM {nombre_tabla}_tallas WHERE uniforme_id = ?', (uniforme_id,)).fetchall()
    
    if request.method == 'POST':
        # Actualizar el uniforme en la tabla de la liga
        conn.execute(f'''
            UPDATE {nombre_tabla}
            SET equipo = ?, color_local = ?, color_visitante = ?
            WHERE id = ?
        ''', (
            request.form['equipo'],
            request.form.get('color_local', ""),
            request.form.get('color_visitante', ""),
            uniforme_id
        ))

        # Actualizar las tallas en la tabla de tallas de la liga
        tallas_nuevas = [
            ("CH", int(request.form.get('cantidad_ch', 0))),
            ("M", int(request.form.get('cantidad_m', 0))),
            ("G", int(request.form.get('cantidad_g', 0)))
        ]
        for talla, cantidad in tallas_nuevas:
            conn.execute(f'''
                UPDATE {nombre_tabla}_tallas
                SET cantidad = ?
                WHERE uniforme_id = ? AND talla = ?
            ''', (cantidad, uniforme_id, talla))
        
        conn.commit()
        conn.close()
        return redirect(url_for('ver_liga', id=liga_id))  # Redirige a la página de la liga
    
    # Mostrar el formulario de actualización de uniforme
    conn.close()
    return render_template_string('''
        <h1>Actualizar Uniforme de {{ liga.nombre }}</h1>
        <form method="POST">
            Equipo: <input type="text" name="equipo" value="{{ uniforme.equipo }}" required><br>
            Color Local: <input type="text" name="color_local" value="{{ uniforme.color_local }}"><br>
            Color Visitante: <input type="text" name="color_visitante" value="{{ uniforme.color_visitante }}"><br>
            Talla CH: <input type="number" name="cantidad_ch" value="{{ tallas[0].cantidad }}"><br>
            Talla M: <input type="number" name="cantidad_m" value="{{ tallas[1].cantidad }}"><br>
            Talla G: <input type="number" name="cantidad_g" value="{{ tallas[2].cantidad }}"><br>
            <button type="submit">Actualizar</button>
        </form>
        <a href="/liga/{{ liga.id }}">Volver a la lista de uniformes</a>
    ''', liga=liga, uniforme=uniforme, tallas=tallas)

# Ruta para eliminar un uniforme de una liga
@app.route('/eliminar_uniforme/<int:liga_id>/<int:uniforme_id>', methods=['POST'])
def eliminar_uniforme(liga_id, uniforme_id):
    conn = get_db_connection()
    liga = conn.execute('SELECT * FROM ligas WHERE id = ?', (liga_id,)).fetchone()
    if liga is None:
        conn.close()
        abort(404, description="Liga no encontrada")
    
    nombre_tabla = f"uniforme_{re.sub(r'[^a-zA-Z0-9]', '_', liga['nombre'].lower())}"
    conn.execute(f'DELETE FROM {nombre_tabla}_tallas WHERE uniforme_id = ?', (uniforme_id,))
    conn.execute(f'DELETE FROM {nombre_tabla} WHERE id = ?', (uniforme_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('ver_liga', id=liga_id))  # Redirige a la página de la liga

if __name__ == '__main__':
    app.run(debug=True)