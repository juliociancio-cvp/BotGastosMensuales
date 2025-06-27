import json
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

DATA_FILE = "data.json"
REINTEGRO_TOPES = {
    "Supermercado": 400000,
    "Combustible": 400000,
    "Tienda": 400000,
    "Bares": 400000,
    "Pagopar": 400000
}

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"ACTIVO": 0, "Ingresos": {}, "Gastos": {}, "Reintegros": {}}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def update_data(category, subcategory, amount):
    data = load_data()
    if subcategory not in data[category]:
        data[category][subcategory] = 0
    data[category][subcategory] += amount
    if category == "Ingresos" or category == "Reintegros":
        data["ACTIVO"] += amount
    elif category == "Gastos":
        data["ACTIVO"] -= amount
    save_data(data)

def update_reintegro(categoria, subcategoria, amount):
    data = load_data()
    if categoria not in data["Reintegros"]:
        data["Reintegros"][categoria] = {}
    if subcategoria not in data["Reintegros"][categoria]:
        data["Reintegros"][categoria][subcategoria] = 0

    total_categoria = sum(data["Reintegros"][categoria].values())
    if total_categoria + amount > REINTEGRO_TOPES.get(categoria, 400000):
        return False, f"Tope mensual excedido para {categoria}. Máximo permitido: 400000"

    data["Reintegros"][categoria][subcategoria] += amount
    data["ACTIVO"] += amount
    save_data(data)
    return True, "Reintegro registrado."

async def ingreso(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        subcat, amount = " ".join(context.args).split(":")
        update_data("Ingresos", subcat.strip(), int(amount.strip()))
        await update.message.reply_text("Ingreso registrado.")
    except:
        await update.message.reply_text("Formato incorrecto. Usa /ingreso Subcategoria: Monto")

async def gasto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        subcat, amount = " ".join(context.args).split(":")
        update_data("Gastos", subcat.strip(), int(amount.strip()))
        await update.message.reply_text("Gasto registrado.")
    except:
        await update.message.reply_text("Formato incorrecto. Usa /gasto Subcategoria: Monto")

