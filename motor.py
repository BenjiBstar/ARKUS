from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import sqlite3
import uvicorn
import os
from urllib.parse import unquote
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse

app = FastAPI()

app.mount("/Datos", StaticFiles(directory="Datos"), name="Datos")
app.mount("/Img", StaticFiles(directory="img"), name="img")

def consultar_boveda(query, parametros=()):
    try:
        conn = sqlite3.connect('boveda_arkus.db') 
        conn.row_factory = sqlite3.Row  
        cursor = conn.cursor()
        cursor.execute(query, parametros)
        resultado = cursor.fetchone()
        conn.close()
        return dict(resultado) if resultado else None
    except Exception as e:
        print(f"Error de enlace: {e}")
        return None

def consultar_multiples_boveda(query, parametros=()):
    try:
        conn = sqlite3.connect('boveda_arkus.db')
        conn.row_factory = sqlite3.Row  
        cursor = conn.cursor()
        cursor.execute(query, parametros)
        resultados = cursor.fetchall()
        conn.close()
        return [dict(row) for row in resultados]
    except Exception as e:
        print(f"Error de enlace: {e}")
        return []

@app.get("/")
def cargar_interfaz():
    return FileResponse("interfaz.html")

# 1. Consulta SQL: País (Barra Superior)
@app.get("/api/pais/{id_pais}")
def obtener_pais(id_pais: str):
    datos = consultar_boveda("SELECT nombre, extension, idh, poblacion FROM paises WHERE id = ?", (unquote(id_pais).lower(),))
    if datos: return datos
    return {"error": "Datos no encontrados"}

# 1B. NUEVO: Consulta SQL Conocimiento (Clics en Extensión, IDH y Población de la Barra Superior)
@app.get("/api/conocimiento/{tema}")
def obtener_conocimiento(tema: str):
    tema_limpio = unquote(tema).strip().lower()
    datos = consultar_boveda("SELECT texto FROM conocimiento WHERE tema = ?", (tema_limpio,))
    if datos:
        return {"texto": datos["texto"]}
    return JSONResponse(status_code=404, content={"error": "Concepto no encontrado en la Bóveda."})

# 2. Consulta SQL: Provincias (Búsqueda Exacta Prioritaria)
@app.get("/api/provincia/{nombre}")
def obtener_provincia(nombre: str):
    nombre_limpio = unquote(nombre).strip()
    # Intento 1: Coincidencia EXACTA (Evita que "Buenos Aires" haga match con "Ciudad Autónoma de Buenos Aires")
    datos = consultar_boveda("SELECT * FROM provincias WHERE jurisdiccion = ? LIMIT 1", (nombre_limpio,))
    # Intento 2: Respaldo por aproximación solo si no hubo coincidencia exacta
    if not datos:
        datos = consultar_boveda("SELECT * FROM provincias WHERE jurisdiccion LIKE ? LIMIT 1", (f"%{nombre_limpio}%",))
    if datos: 
        return dict(datos)
    return {"error": "Jurisdicción terrestre no indexada en la Bóveda"}

# 3. Consulta SQL: Espacios Marítimos
@app.get("/api/espacio_maritimo/{id_capa}")
def obtener_espacio_maritimo(id_capa: str):
    datos = consultar_boveda("SELECT * FROM espacios_maritimos WHERE id_capa = ?", (unquote(id_capa),))
    if datos: return dict(datos)
    return {"error": "Capa naval no indexada en la Bóveda"}

# 4. Consulta SQL: Fuerzas Armadas (General)
@app.get("/api/fuerzas/{id_fuerza}")
def obtener_fuerza(id_fuerza: str):
    datos = consultar_boveda("SELECT * FROM fuerzas WHERE id = ?", (unquote(id_fuerza),))
    if datos:
        return {
            "nombre": datos['nombre'],
            "logo": datos['logo'],
            "foto": datos['foto'],
            "descripcion1": datos['desc1'],
            "descripcion2": datos['desc2'],
            "area_ops": datos['area_ops'],
            "unidades_superficie": datos['unidades_superficie']
        }
    return {"error": "Base no encontrada"}

# 5. Consulta SQL: Vistazo Rápido
@app.get("/api/vistazo/{id_fuerza}")
def obtener_vistazo(id_fuerza: str):
    datos = consultar_boveda("SELECT nombre, tipo_base, unidades_corto FROM fuerzas WHERE id = ?", (unquote(id_fuerza),))
    if datos:
        return {
            "titulo": datos['nombre'],
            "tipo": datos['tipo_base'],
            "unidades": datos['unidades_corto']
        }
    return {"error": "Sin datos"}

# 6. Consulta SQL: Aeropuertos (Búsqueda Táctica Mejorada)
@app.get('/api/aeropuerto/{identificador}')
def get_aeropuerto(identificador: str):
    ident_limpio = unquote(identificador).strip()
    
    fila = consultar_boveda('''
        SELECT * FROM aeropuertos 
        WHERE codigo = ? OR nombre = ?
        LIMIT 1
    ''', (ident_limpio, ident_limpio))
    
    if not fila:
        fila = consultar_boveda('''
            SELECT * FROM aeropuertos 
            WHERE nombre LIKE ? OR codigo LIKE ?
            LIMIT 1
        ''', (f'%{ident_limpio}%', f'%{ident_limpio}%'))

    if fila:
        return {
            "nombre": fila.get("nombre"),
            "codigo": fila.get("codigo"),
            "superficie": fila.get("superficie") or fila.get("pistas") or "Asfalto",
            "empresa": fila.get("empresa") or fila.get("explotador") or "ANAC",
            "provincia": fila.get("provincia"),
            "direccion": fila.get("direccion"),
            "concesionado": fila.get("concesionado"),
            "nivel_prioridad": fila.get("nivel_prioridad") or "NIVEL 2 - AERÓDROMO REGIONAL",
            "evaluacion_tactica": fila.get("evaluacion_tactica") or "Infraestructura aeronáutica de enlace federal."
        }
        
    return JSONResponse(status_code=404, content={"error": "Aeropuerto no encontrado en la Bóveda."})

# 7. Consulta SQL: Países Internacionales (Con Perfiles Geopolíticos Reales)
PERFILES_PAISES = {
    "República de Chile": "Frontera cordillerana de 5.308 km. Vector clave para la proyección bioceánica hacia el Pacífico, pasos andinos estratégicos y control compartido del Estrecho de Magallanes y Canal Beagle.",
    "República Federativa de Brasil": "Principal socio estratégico del MERCOSUR y potencia industrial regional. Eje vital de interconexión energética, comercio automotriz y seguridad en la Cuenca del Plata.",
    "Estado Plurinacional de Bolivia": "Frontera crítica del teatro NOA. Nodo de interconexión gasífera histórica (Gasoducto Norte), tránsito vecinal intensivo y corredor del Triángulo del Litio.",
    "República del Paraguay": "Actor central en la Hidrovía Paraná-Paraguay y socio estratégico en generación hidroeléctrica binacional (Entidad Binacional Yacyretá). Requiere vigilancia fluvial conjunta.",
    "República Oriental del Uruguay": "Socio binacional en la administración del Río de la Plata, Río Uruguay y el complejo hidroeléctrico de Salto Grande. Nodo clave de acceso marítimo a la Cuenca del Plata."
}

@app.get("/api/pais_internacional/{nombre}")
def obtener_pais_internacional(nombre: str):
    nombre_limpio = unquote(nombre).strip()
    resultado = consultar_boveda("SELECT nombre, poblacion, extension, idh, escudo, bandera FROM paises WHERE nombre = ? OR id = ? LIMIT 1", (nombre_limpio, nombre_limpio.lower()))
    
    if resultado:
        nom_oficial = resultado["nombre"]
        return {
            "nombre": nom_oficial,
            "poblacion": resultado["poblacion"],
            "extension": resultado["extension"],
            "idh": resultado["idh"],
            "escudo": resultado["escudo"],
            "bandera": resultado["bandera"], 
            "resumen_tactico": PERFILES_PAISES.get(nom_oficial, "Estado limítrofe del teatro geopolítico sudamericano.")
        }
    return {"error": "País no encontrado en la Bóveda"}

# 8. Consulta SQL: Bases Militares y Unidades Desplegadas (OrBat)
@app.get("/api/tactico/base/{nombre_base}")
def obtener_despliegue_tactico(nombre_base: str):
    nom_limpio = unquote(nombre_base).strip()
    base = consultar_boveda("SELECT * FROM bases_militares WHERE nombre = ? OR nombre LIKE ? LIMIT 1", (nom_limpio, f"%{nom_limpio}%"))
    if not base:
        return JSONResponse(status_code=404, content={"error": "Instalación no registrada en el esquema táctico."})
    unidades = consultar_multiples_boveda("SELECT nombre_unidad, tipo, equipamiento FROM unidades_desplegadas WHERE id_base = ?", (base["id_base"],))
    return {
        "nombre": base["nombre"],
        "fuerza": base["fuerza"],
        "comando": base["comando_jurisdiccion"],
        "unidades": unidades
    }

# 9. Consulta SQL: Perfil Bioclimático (16 Climas ANIDA Cubiertos)
DEFINICIONES_CLIMA = {
    "Subtropical con estación seca": "Temperaturas elevadas con estación seca invernal. Afecta el desplazamiento logístico por polvo en suspensión y escasez hídrica superficial.",
    "Subtropical sin estación seca": "Alta humedad y precipitaciones constantes todo el año. Entorno selvático/boscoso que dificulta la observación aérea y la movilidad fuera de ruta.",
    "Subtropical serrano": "Variaciones térmicas y pluviométricas condicionadas por la altitud orográfica (Yungas). Nubosidad baja frecuente que restringe operaciones aéreas.",
    "Pampeano": "Clima templado con lluvias regulares. Terreno llano altamente transitable, óptimo para despliegues mecanizados y operaciones aéreas todo el año.",
    "Oceánico": "Influencia marítima moderadora con alta humedad y nieblas costeras frecuentes que reducen la visibilidad en operaciones litorales.",
    "De la estepa patagónica": "Aridez extrema, fuertes vientos constantes del oeste y escasa cobertura vegetal. Máxima visibilidad satelital/ISR, clima hostil invernal.",
    "Frío o patagónico": "Inviernos rigurosos con heladas y vientos severos. Exige aditivos anticongelantes en combustibles y vestuario térmico para operaciones sostenidas.",
    "Húmedo de los Andes patagónico-fueguinos": "Abundantes precipitaciones níveas y pluviales. Pasos cordilleranos susceptibles a cierre invernal; movilidad restringida a corredores viales.",
    "Nival": "Hielos perpetuos y nevadas constantes en alta montaña. Operación exclusiva para tropas de Cazadores de Montaña.",
    "Antártico": "Frío polar extremo (< -20 °C) y vientos catabáticos. Requiere logística antártica dedicada (COCOANTAR) y equipamiento polar nivel 3.",
    "De transición": "Zona semiárida de encuentro entre frentes húmedos y secos. Terreno firme apto para columnas blindadas, con tormentas convectivas estivales.",
    "Andino puneño": "Hipoxia de gran altitud (>3.500 msnm) y amplitud térmica extrema. Pérdida severa de potencia en motores de combustión y rotores de helicópteros.",
    "De sierras y campos": "Condiciones templadas estables con lluvias estivales concentradas. Buena aptitud táctica para el desplazamiento de unidades ligeras.",
    "Serrano": "Microclimas topográficos y vientos canalizados en valles. Requiere retransmisores en cotas altas para asegurar enlaces de comunicaciones VHF/UHF.",
    "Magallánico": "Clima subpolar ventoso con nubosidad baja constante. Ventanas reducidas para reconocimiento aéreo e interdicción marítima en el Atlántico Sur.",
    "Insular oceánico": "Turbulencia marítima y vientos subantárticos permanentes. Complejidad extrema para maniobras de apontaje y reabastecimiento naval."
}

@app.get("/api/clima/{nombre_clima}")
def obtener_inteligencia_climatica(nombre_clima: str):
    nombre_limpio = unquote(nombre_clima).strip()
    resultado = consultar_boveda("SELECT * FROM intel_climas WHERE clima = ? OR clima LIKE ? LIMIT 1", (nombre_limpio, f"%{nombre_limpio}%"))
    if not resultado:
        return JSONResponse(status_code=404, content={"error": "Clasificación climática no encontrada en la Bóveda."})
    
    evaluacion = resultado.get("evaluacion_tactica") or DEFINICIONES_CLIMA.get(resultado["clima"]) or DEFINICIONES_CLIMA.get(nombre_limpio, "Condiciones meteorológicas regionales bajo monitoreo del SMN.")
    return {
        "clima": resultado["clima"],
        "tipo": resultado["tipo"],
        "evaluacion_tactica": evaluacion,
        "temperatura": resultado.get("temperatura") or "ND",
        "precipitacion": resultado.get("precipitacion") or "ND"
    }

# 10. Consulta SQL: Biomas (Con traductor de nombres GeoJSON -> SQLite)
MAPEO_BIOMAS = {
    "Selva Misionera": "Selva Paranaense",
    "Bosque Andino Patagonico": "Bosque Andino Patagónico",
    "Parque Chaqueno": "Parque Chaqueño"
}

@app.get("/api/bioma/{region}")
def obtener_bioma(region: str):
    reg_limpia = unquote(region).strip()
    reg_busqueda = MAPEO_BIOMAS.get(reg_limpia, reg_limpia)
    resultado = consultar_boveda("SELECT * FROM intel_biomas WHERE region = ? OR region LIKE ? LIMIT 1", (reg_busqueda, f"%{reg_busqueda}%"))
    if resultado: return dict(resultado)
    return JSONResponse(status_code=404, content={"error": "Región fitogeográfica no indexada en la Bóveda."})

# 11. Consulta SQL: Cuencas Hídricas
@app.get("/api/cuenca/{cuenca:path}")
def obtener_cuenca(cuenca: str):
    cuenca_limpia = unquote(cuenca).strip()
    resultado = consultar_boveda("SELECT * FROM intel_cuencas WHERE cuenca = ? OR cuenca LIKE ? LIMIT 1", (cuenca_limpia, f"%{cuenca_limpia}%"))
    if resultado: return dict(resultado)
    return JSONResponse(status_code=404, content={"error": "Vector hídrico no indexado en la Bóveda."})

# 12. Consulta SQL: Ferrocarriles
@app.get("/api/ferrocarril/{ramal:path}")
def obtener_ferrocarril(ramal: str):
    ramal_limpio = unquote(ramal).strip()
    resultado = consultar_boveda("SELECT * FROM intel_ferroviaria WHERE ramal = ? OR fna = ? OR ramal LIKE ? OR fna LIKE ? LIMIT 1", (ramal_limpio, ramal_limpio, f"%{ramal_limpio}%", f"%{ramal_limpio}%"))
    if resultado: return dict(resultado)
    return JSONResponse(status_code=404, content={"error": "Vector logístico no indexado."})

# 13. Consulta SQL: Industrias
@app.get("/api/industria/{nombre:path}")
def obtener_industria(nombre: str):
    nom_limpio = unquote(nombre).strip()
    resultado = consultar_boveda("SELECT * FROM infra_productiva WHERE nombre = ? OR nombre LIKE ? LIMIT 1", (nom_limpio, f"%{nom_limpio}%"))
    if resultado: return dict(resultado)
    return JSONResponse(status_code=404, content={"error": "Complejo industrial no indexado en la Bóveda."})

# 14. Consulta SQL: Puertos (Devuelve SELECT * incluyendo la nueva columna 'evaluacion')
@app.get("/api/puerto/{nombre:path}")
def obtener_puerto(nombre: str):
    nom_limpio = unquote(nombre).strip()
    resultado = consultar_boveda("SELECT * FROM infra_portuaria WHERE nombre = ? OR nombre LIKE ? LIMIT 1", (nom_limpio, f"%{nom_limpio}%"))
    if resultado: return dict(resultado)
    return JSONResponse(status_code=404, content={"error": "Puerto no indexado en la Bóveda."})


# =====================================================================
# ENDPOINT MAESTRO UNIVERSAL PARA LA INYECCIÓN MASIVA C4ISR
# =====================================================================
@app.get("/api/arkus/{tabla}/{identificador:path}")
def inteligencia_dinamica(tabla: str, identificador: str):
    tablas_autorizadas = [
        "energia_alta_tension", "energia_centrales", "energia_nodos_gen", "energia_presion_gas", 
        "energia_presas", "energia_gasoductos", "logistica_vial_nac", "logistica_vial_prov", 
        "logistica_espacio_aereo", "telecom_cables", "infra_agua", "soberania_mar_terr", 
        "soberania_zee", "soberania_plataforma", "desastres_sismos_hist", "desastres_sismos_zonas", 
        "desastres_volcanes_areas", "desastres_volcanes_puntos", "desastres_incendios", 
        "desastres_hectareas", "intel_metaliferos", "intel_industriales"
    ]
    
    if tabla not in tablas_autorizadas:
        return JSONResponse(status_code=403, content={"error": "Nivel de autorización insuficiente para este sector de la Bóveda."})
    
    identificador_limpio = unquote(identificador).strip()
    
   # Interceptor directo en el motor para el Gasoducto de 36"
    if tabla == "energia_gasoductos" and any(k in identificador_limpio for k in ["Pascasio", "Moreno", "Kirchner"]):
        return {
            "id_obj": "GPM-36",
            "nombre_clave": "Gasoducto Perito Francisco Pascasio Moreno",
            "Tramo": "Tratayén (Neuquén) - Salliqueló (Buenos Aires)",
            "Licenciataria": "Energía Argentina S.A. (ENARSA)",
            "Diametro": "36",
            "nivel_prioridad": "NIVEL 1 - ARTERIA ENERGÉTICA NACIONAL (36\")",
            "evaluacion_tactica": "Gasoducto troncal estratégico de 36 pulgadas. Evacúa el gas no convencional de la Cuenca Neuquina (Vaca Muerta) hacia el anillo central del país, abasteciendo centrales termoeléctricas e industrias críticas."
        }

    # Búsqueda limpia compatible con todas las tablas (incluida Minería)
    resultado = consultar_boveda(
        f"SELECT * FROM {tabla} WHERE id_obj = ? OR nombre_clave LIKE ? LIMIT 1", 
        (identificador_limpio, f"%{identificador_limpio}%")
    )
    
    if resultado:
        return dict(resultado)
        
    return JSONResponse(status_code=404, content={"error": "Expediente clasificado o no encontrado en la Bóveda."})
# ==========================================
# RUTA PARA SERVIR LA INTERFAZ CON EL TOKEN SEGURO
# ==========================================
@app.get("/")
def home():
    mapbox_token = os.environ.get("MAPBOX_TOKEN", "NO_LLEGO_NADA")
    print(f"=== TOKEN RECIBIDO DE RENDER: {mapbox_token} ===")
    
    with open("interfaz.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    
    html_content = html_content.replace("TU_TOKEN_AQUI", mapbox_token)
    
    print(f"=== HTML REEMPLAZADO EXITOSAMENTE ===")
    return HTMLResponse(content=html_content)

# =====================================================================
# ARRANQUE PREPARADO PARA SERVIDORES EN LA NUBE (RENDER)
# =====================================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("motor:app", host="0.0.0.0", port=port)
