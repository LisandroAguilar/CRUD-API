from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(
    title="API de Uniformes Deportivos",
    description="API simple para gestionar inventario de uniformes deportivos",
    version="1.0.0"
)

db_uniformes = []
class Uniforme(BaseModel):
    equipo: str
    talla: str
    stock: int
    precio: float

class UniformeConID(Uniforme):
    id: int

@app.post("/uniformes/", response_model=UniformeConID, summary="Agregar uniforme")
def crear_uniforme(uniforme: Uniforme):
    """Crea un nuevo uniforme en el inventario"""
    nuevo_id = len(db_uniformes) + 1
    uniforme_con_id = UniformeConID(id=nuevo_id, **uniforme.dict())
    db_uniformes.append(uniforme_con_id)
    return uniforme_con_id

@app.get("/uniformes/", response_model=List[UniformeConID], summary="Listar uniformes")
def listar_uniformes():
    """Obtiene todos los uniformes disponibles"""
    return db_uniformes

@app.get("/uniformes/{id}", response_model=UniformeConID, summary="Obtener uniforme")
def obtener_uniforme(id: int):
    """Obtiene un uniforme específico por su ID"""
    if id < 1 or id > len(db_uniformes):
        raise HTTPException(status_code=404, detail="Uniforme no encontrado")
    return db_uniformes[id-1]

@app.put("/uniformes/{id}", response_model=UniformeConID, summary="Actualizar uniforme")
def actualizar_uniforme(id: int, uniforme: Uniforme):
    """Actualiza los datos de un uniforme existente"""
    if id < 1 or id > len(db_uniformes):
        raise HTTPException(status_code=404, detail="Uniforme no encontrado")
    
    uniforme_actualizado = UniformeConID(id=id, **uniforme.dict())
    db_uniformes[id-1] = uniforme_actualizado
    return uniforme_actualizado

@app.delete("/uniformes/{id}", summary="Eliminar uniforme")
def eliminar_uniforme(id: int):
    """Elimina un uniforme del inventario"""
    if id < 1 or id > len(db_uniformes):
        raise HTTPException(status_code=404, detail="Uniforme no encontrado")
    
    db_uniformes.pop(id-1)
    return {"mensaje": "Uniforme eliminado correctamente"}