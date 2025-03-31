from supabase import create_client
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def obtener_mascotas(user_email):
    """Obtiene las mascotas del usuario autenticado usando su ID en lugar de su email"""

    # 📌 Obtener el UUID del usuario basado en su email
    propietario_id = obtener_usuario_id(user_email)

    if propietario_id is None:
        return []

    # 📌 Ahora filtramos por `propietario_id` en lugar de `propietario_email`
    response = supabase.table("mascotas").select("*").eq("propietario_id", propietario_id).execute()
    return response.data if response.data else []


def obtener_usuario_id(email):
    """Obtiene el ID del usuario a partir del email"""
    response = supabase.table("usuarios").select("id").eq("email", email).single().execute()
    if response.data:
        return response.data["id"]
    return None

def registrar_mascota(nombre, especie, raza, color, tamano, nacimiento, propietario_email):
    """Registra una mascota en la base de datos"""
    
    # 📌 Convertir email a ID
    propietario_id = obtener_usuario_id(propietario_email)
    
    if propietario_id is None:
        return {"error": "No se encontró el usuario con ese email"}

    # 📌 Guardar la mascota en la base de datos usando propietario_id
    response = supabase.table("mascotas").insert({
        "nombre": nombre,
        "especie": especie,
        "raza": raza,
        "color": color,
        "tamano": tamano,
        "anio_nacimiento": nacimiento,
        "propietario_id": propietario_id  # ✅ Usamos ID en lugar de email
    }).execute()

    return response


def obtener_tarifa_servicio(servicio_nombre):
    """Obtiene la tarifa estándar de un servicio desde la base de datos"""
    response = supabase.table("servicios").select("id, tarifa, periodicidad").eq("nombre", servicio_nombre).execute()
    if response.data:
        return response.data[0]  # Devuelve ID, tarifa y periodicidad del servicio
    return None

def registrar_historial(mascota_id, servicio_nombre, veterinario=None):
    """Registra un servicio en el historial clínico y programa un aviso si es periódico"""
    
    servicio_info = obtener_tarifa_servicio(servicio_nombre)
    if not servicio_info:
        return {"error": "El servicio no existe en la base de datos"}

    data = {
        "mascota_id": mascota_id,
        "servicio_id": servicio_info['id'],
        "servicio": servicio_nombre,
        "costo": servicio_info['tarifa'],
        "veterinario": veterinario
    }

    response = supabase.table("historial_clinico").insert(data).execute()

    # Si el servicio tiene periodicidad, generamos un aviso
    if servicio_info['periodicidad']:
        fecha_proxima = datetime.now() + timedelta(days=servicio_info['periodicidad'])
        aviso = {
            "mascota_id": mascota_id,
            "mensaje": f"Recuerda programar el próximo servicio de {servicio_nombre} para el {fecha_proxima.strftime('%Y-%m-%d')}",
            "fecha_recordatorio": fecha_proxima.strftime('%Y-%m-%d')
        }
        supabase.table("avisos").insert(aviso).execute()

    return response


def generar_factura(cliente_email, mascota_id):
    """Genera una factura para todos los servicios realizados a una mascota"""

    # Obtener historial clínico de la mascota
    response = supabase.table("historial_clinico").select("*").eq("mascota_id", mascota_id).execute()
    historial = response.data if response.data else []

    if not historial:
        return {"error": "No hay servicios registrados para facturar"}

    total = sum([servicio["costo"] for servicio in historial])
    
    factura = {
        "cliente_email": cliente_email,
        "mascota_id": mascota_id,
        "total": total,
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    response = supabase.table("facturas").insert(factura).execute()
    return response

def obtener_facturas(email_cliente):
    """Obtiene todas las facturas asociadas a un cliente"""
    response = supabase.table("facturas").select("id, fecha, mascota_id, total").eq("cliente_email", email_cliente).execute()
    return response.data if response.data else []

def obtener_usuarios():
    response = supabase.table("usuarios").select("id, email, rol").execute()
    return response.data if response.data else []

def eliminar_usuario(usuario_id):
    supabase.table("usuarios").delete().eq("id", usuario_id).execute()

def eliminar_mascota(mascota_id):
    supabase.table("mascotas").delete().eq("id", mascota_id).execute()

def agregar_veterinario(email):
    supabase.table("usuarios").update({"rol": "Veterinario"}).eq("email", email).execute()

def eliminar_veterinario(vet_id):
    supabase.table("usuarios").update({"rol": "Cliente"}).eq("id", vet_id).execute()

def obtener_historial(mascota_id):
    """Obtiene el historial clínico de una mascota"""
    response = supabase.table("historial_clinico").select("*").eq("mascota_id", mascota_id).execute()
    historial = response.data if response.data else []

    mascota_response = supabase.table("mascotas").select("id", "nombre", "especie").eq("id", mascota_id).execute()
    
    if not mascota_response.data:
        return historial, None  # Retornar historial vacío y mascota como None si no se encuentra la mascota

    mascota = mascota_response.data[0]  # Guardar datos de la mascota

    return historial, mascota  # 🔹 Ahora sí retorna dos valores


def agregar_historial(mascota_id, descripcion, fecha):
    """Añade una nueva entrada al historial clínico de una mascota"""
    data = {
        "mascota_id": mascota_id,
        "descripcion": descripcion,
        "fecha": fecha
    }
    response = supabase.table("historial_clinico").insert(data).execute()
    return response.data if response.data else None
