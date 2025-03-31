from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def registrar_usuario(email, password, username, telefono):
    """Registra un usuario en Supabase Auth y en la base de datos"""
    try:
        # 1️⃣ Registrar en Supabase Auth
        auth_response = supabase.auth.sign_up({"email": email, "password": password})

        if hasattr(auth_response, "error") and auth_response.error:
            return {"error": auth_response.error.message}

        user_id = auth_response.user.id  # Obtener el UID del usuario en Supabase Auth

        # 2️⃣ Guardar en la tabla "usuarios" en la BD
        data = {
            "id": user_id,  # Usamos el UID de Supabase Auth como ID
            "email": email,
            "username": username,
            "telefono": telefono
        }
        db_response = supabase.table("usuarios").insert(data).execute()

        if hasattr(db_response, "error") and db_response.error:
            return {"error": db_response.error.message}

        return {"success": "Usuario registrado correctamente"}

    except Exception as e:
        return {"error": str(e)}

def iniciar_sesion(email, password):
    """Inicia sesión en Supabase y devuelve el token"""
    try:
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})

        if hasattr(response, "error") and response.error:
            return {"error": response.error.message}

        # Verificar que se haya recibido una sesión válida
        if not hasattr(response, "session") or not response.session:
            return {"error": "No se pudo obtener la sesión. Verifica las credenciales."}

        return {"success": "Inicio de sesión exitoso", "session": response.session}

    except Exception as e:
        return {"error": str(e)}

def cerrar_sesion():
    """Cierra sesión eliminando el token"""
    supabase.auth.sign_out()
    return {"message": "Sesión cerrada"}
