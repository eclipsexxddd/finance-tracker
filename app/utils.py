import sys, os
import csv
from pathlib import Path
from app.db import add_transaction, get_transactions, get_categories, add_category, clear_transactions

def export_csv(path: str):
    rows = get_transactions()
    keys = ['date', 'amount', 'type', 'category_name', 'note']
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for r in rows:
            writer.writerow({
                'date': r['date'],
                'amount': r['amount'],
                'type': r['type'],
                'category_name': r.get('category_name') or '',
                'note': r.get('note') or ''
            })


def import_csv(path: str):
    # загружаем все категории
    cats = {c['name']: c['id'] for c in get_categories()}
    # очистка
    clear_transactions()

    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            date = row.get('date')
            amount = float(row.get('amount', 0))
            ttype = row.get('type', 'Трата')
            catname = row.get('category_name') or row.get('category') or 'Без категории'

            # создаём категорию если её нет
            if catname not in cats:
                new_id = add_category(catname, None)
                cats[catname] = new_id

            cat_id = cats[catname]
            note = row.get('note', '')
            add_transaction(date, amount, ttype, cat_id, note)
