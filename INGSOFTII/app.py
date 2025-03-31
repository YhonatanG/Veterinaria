from flask import Flask, render_template, request, redirect, url_for, session
from auth import registrar_usuario, iniciar_sesion, cerrar_sesion
from services import (
    obtener_mascotas, registrar_mascota, obtener_historial, agregar_historial, 
    eliminar_mascota, obtener_usuarios, eliminar_usuario, agregar_veterinario, 
    eliminar_veterinario, obtener_facturas
)

from supabase import create_client, Client
import os

# 📌 Configuración de Supabase
SUPABASE_URL = "https://xcrpqegknjqcgphsxkib.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhjcnBxZWdrbmpxY2dwaHN4a2liIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDEwMjI4MTUsImV4cCI6MjA1NjU5ODgxNX0.waj01OtWr3hFxZ34IR1W2y13-VyZu_G0118tgMVpRYY"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)
app.secret_key = "clave_secreta_segura"

# 📌 Rutas de Autenticación
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        response = iniciar_sesion(email, password)

        if "error" in response:
            return f"<h3 style='color:red;'>Error en el inicio de sesión: {response['error']}</h3>"

        session['user'] = response['session'].access_token
        session['user_email'] = email

        # Obtener rol del usuario
        user_data = supabase.table("usuarios").select("rol").eq("email", email).execute()
        if user_data.data:
            session['rol'] = user_data.data[0]['rol']

        return redirect(url_for('menu'))

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        username = request.form['username']
        telefono = request.form['telefono']

        response = registrar_usuario(email, password, username, telefono)

        if "error" in response:
            return f"<h3 style='color:red;'>Error en el registro: {response['error']}</h3>"

        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/logout')
def logout():
    session.clear()
    cerrar_sesion()
    return redirect(url_for('login'))

# 📌 Menú Principal
@app.route('/')
def menu():
    if 'user' not in session:
        return redirect(url_for('login'))

    mascotas = obtener_mascotas(session['user_email'])
    return render_template('menu.html', user_email=session['user_email'], mascotas=mascotas, rol=session.get('rol'))

# 📌 Ruta para ver Mascotas
@app.route('/ver-mascotas')
def ver_mascotas():
    if 'user' not in session:
        return redirect(url_for('login'))
    mascotas = obtener_mascotas(session['user_email'])
    return render_template('ver_mascotas.html', mascotas=mascotas, rol=session.get('rol'))

@app.route('/registrar-mascota', methods=['GET', 'POST'])
def registrar_mascota_view():
    if 'user' not in session:
        return redirect(url_for('login'))

    mensaje = None
    mascota_registrada = None

    if request.method == 'POST':
        nombre = request.form['nombre']
        especie = request.form['especie']
        raza = request.form['raza']
        color = request.form['color']
        tamano = request.form['tamano']
        nacimiento = int(request.form['nacimiento'])
        propietario_email = session['user_email']

        response = registrar_mascota(nombre, especie, raza, color, tamano, nacimiento, propietario_email)

        if "error" in response:
            mensaje = "Hubo un error al registrar la mascota."
        else:
            mensaje = "Mascota registrada exitosamente."
            mascota_registrada = {
                "nombre": nombre,
                "especie": especie,
                "raza": raza,
                "color": color,
                "tamano": tamano,
                "anio_nacimiento": nacimiento
            }

    return render_template('rmascota.html', mensaje=mensaje, mascota=mascota_registrada)

# 📌 Ruta para ver Historial Clínico
@app.route('/historial')
def ver_historial():
    if 'user' not in session:
        return redirect(url_for('login'))

    # 🔍 Obtener usuario_id basado en su email
    usuario = supabase.table("usuarios").select("id").eq("email", session['user_email']).single().execute()

    if not usuario.data:
        return "<h3 style='color:red;'>Error: Usuario no encontrado</h3>"

    usuario_id = usuario.data["id"]

    # 🔍 Obtener todas las mascotas del usuario
    mascotas = supabase.table("mascotas").select("*").eq("propietario_id", usuario_id).execute()

    if not mascotas.data:
        mascotas = []
    else:
        mascotas = mascotas.data

    # 🔍 Obtener historial clínico de todas las mascotas del usuario
    historial = supabase.table("historial_clinico").select("*").execute()
    
    if not historial.data:
        historial = []
    else:
        historial = historial.data

    # 🔍 Obtener citas agendadas de todas las mascotas del usuario
    citas = (
    supabase.table("citas")
    .select("id, mascota_id, fecha, hora, estado, servicio_id, servicios!citas_servicio_id_fkey(nombre)")
    .execute())
    
    if not citas.data:
        citas = []
    else:
        citas = citas.data

    # 🔍 Obtener información de los servicios para mostrar el nombre en lugar del ID
    servicios = supabase.table("servicios").select("*").execute()
    
    servicios_dict = {servicio["id"]: servicio["nombre"] for servicio in servicios.data} if servicios.data else {}

    return render_template('historial.html', mascotas=mascotas, historial=historial, citas=citas, servicios=servicios_dict)


@app.route('/agendar-cita', methods=['GET', 'POST'])
def agendar_cita():
    if 'user' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        mascota_id = request.form['mascota']
        fecha = request.form['fecha']
        hora = request.form['hora']
        servicio_id = request.form.get('servicio_id')  # ✅ Usa .get() para evitar KeyError
  # ✅ Cambiado a servicio_id

        # 🔍 Buscar usuario_id basado en su email
        usuario = supabase.table("usuarios").select("id").eq("email", session['user_email']).single().execute()
        
        if not usuario.data:  # 🚨 Si no se encuentra el usuario
            return "<h3 style='color:red;'>Error: Usuario no encontrado</h3>"

        usuario_id = usuario.data["id"]  # ✅ Obtener usuario_id

        # ✅ Insertar la cita con servicio_id en vez de servicio
        supabase.table("citas").insert({
            "mascota_id": mascota_id,
            "usuario_id": usuario_id,  
            "fecha": fecha,
            "hora": hora,
            "servicio_id": servicio_id  # ✅ Ahora usa servicio_id
        }).execute()

        return redirect(url_for('menu'))

    mascotas = obtener_mascotas(session['user_email'])
    servicios = supabase.table("servicios").select("id", "nombre").execute().data  # ✅ Obtener servicios disponibles

    return render_template('agendar_cita.html', mascotas=mascotas, servicios=servicios)



# 📌 Ruta para agregar información al historial (Solo Veterinarios)
@app.route('/historial/agregar/<mascota_id>', methods=['POST'])
def agregar_historial_view(mascota_id):
    if 'user' not in session or session.get('rol') != 'Veterinario':
        return redirect(url_for('menu'))

    descripcion = request.form['descripcion']
    agregar_historial(mascota_id, descripcion)
    
    return redirect(url_for('ver_historial', mascota_id=mascota_id))

# 📌 Ruta para ver Facturación
@app.route('/facturacion')
def facturacion():
    if 'user' not in session:
        return redirect(url_for('login'))
    facturas = obtener_facturas(session['user_email'])
    return render_template('facturacion.html', facturas=facturas, rol=session.get('rol'))

# 📌 Rutas del Administrador
@app.route('/admin/usuarios')
def admin_usuarios():
    if 'user' not in session or session.get('rol') != 'Administrador':
        return redirect(url_for('menu'))
    usuarios = obtener_usuarios()
    return render_template('admin_usuarios.html', usuarios=usuarios)

@app.route('/admin/eliminar_usuario/<usuario_id>')
def eliminar_usuario_view(usuario_id):
    if 'user' not in session or session.get('rol') != 'Administrador':
        return redirect(url_for('menu'))

    eliminar_usuario(usuario_id)
    return redirect(url_for('admin_usuarios'))

@app.route('/eliminar_mascota/<mascota_id>')
def eliminar_mascota_view(mascota_id):
    if 'user' not in session:
        return redirect(url_for('login'))

    # Eliminar la mascota sin verificar el rol
    eliminar_mascota(mascota_id)
    
    return redirect(url_for('ver_mascotas'))


def mascota_pertenece_a_usuario(mascota_id, user_email):
    mascota = supabase.table("mascotas").select("propietario_email").eq("id", mascota_id).execute()
    return mascota.data and mascota.data[0]['propietario_email'] == user_email

@app.route('/admin/agregar_veterinario', methods=['POST'])
def agregar_veterinario_view():
    if 'user' not in session or session.get('rol') != 'Administrador':
        return redirect(url_for('menu'))

    email = request.form['email']
    agregar_veterinario(email)
    return redirect(url_for('admin_usuarios'))

@app.route('/admin/eliminar_veterinario/<vet_id>')
def eliminar_veterinario_view(vet_id):
    if 'user' not in session or session.get('rol') != 'Administrador':
        return redirect(url_for('admin_usuarios'))

    eliminar_veterinario(vet_id)
    return redirect(url_for('admin_usuarios'))

@app.route('/avisos')
def avisos():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('avisos.html')
 
if __name__ == '__main__':
    app.run(debug=True)

# Configurar el puerto dinámico de Render
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))  # Usar el puerto de Render o 10000 por defecto
    app.run(host="0.0.0.0", port=port)
