import json
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

DATA_FILE = "data.json"

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

async def reintegro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        subcat, amount = " ".join(context.args).split(":")
        update_data("Reintegros", subcat.strip(), int(amount.strip()))
        await update.message.reply_text("Reintegro registrado.")
    except:
        await update.message.reply_text("Formato incorrecto. Usa /reintegro Subcategoria: Monto")

async def informe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    lines = [f"ACTIVO: {data['ACTIVO']}\n"]
    for cat in ["Ingresos", "Gastos", "Reintegros"]:
        lines.append(f"{cat}:")
        for subcat, amount in data[cat].items():
            lines.append(f"  {subcat}: {amount}")
        lines.append("")
    await update.message.reply_text("\n".join(lines))

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    TOKEN = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("ingreso", ingreso))
    app.add_handler(CommandHandler("gasto", gasto))
    app.add_handler(CommandHandler("reintegro", reintegro))
    app.add_handler(CommandHandler("informe", informe))
    app.run_polling()
