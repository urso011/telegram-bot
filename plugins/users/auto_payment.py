import asyncio
import re
import time
from typing import Union

from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    ForceReply,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    User,
)

from config import ADMIN_CHAT
from config import GRUPO_PUB
from config import BOT_LINK
from config import BOT_LINK_SUPORTE
from database import cur, save
from payments import (
    AUTO_PAYMENTS,
    Gerencianet,
    GerencianetCredentials,
    Juno,
    JunoCredentials,
    MercadoPago,
    PagBank,
    PagBankCredentials,
)
from utils import (
    create_copy_paste_pix,
    create_mention,
    get_support_user,
    insert_sold_balance,
)


def cpf_validate(numbers) -> bool:
    cpf = [int(char) for char in numbers if char.isdigit()]
    if len(cpf) != 11:
        return False
    if cpf == cpf[::-1]:
        return False
    for i in range(9, 11):
        value = sum((cpf[num] * ((i + 1) - num) for num in range(0, i)))
        digit = ((value * 10) % 11) % 10
        if digit != cpf[i]:
            return False
    return True


async def verify_pay(objeto, c: Client, send, value: float):
    refer_bonus = (value / 100) * 5

    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Voltar", callback_data="start")]]
    )

    start_time = time.time()

    mult = 6 if objeto.c in ["PagBank", "GerenciaNet", "Juno"] else 30

    while time.time() - start_time < (
        mult * 60
    ):  # Esperando por 6 minutos, vai que né...
        rt = await objeto.verify()
        #rt = "PAGO"
        if rt == "PAGO":
           ## rt = "PAGO"
            saldobonus1 = cur.execute("SELECT valordobro FROM dobrosaldo").fetchone()[0]
            saldobonus = float(saldobonus1)
            saldobonus = value*saldobonus/100
            saldodobro = value + saldobonus
            refer, username, name = cur.execute(
                "SELECT refer, username, name_user FROM users WHERE id = ?",
                [objeto.user_id],
            ).fetchone()

            cur.execute(
                "UPDATE users SET balance = round(balance + ?, 2) WHERE id = ?",
                [saldodobro, objeto.user_id],
            )

            await send.edit_text(
                f"<b>✅ Agora sim 🎉 o pagamento foi concluido e R$ {value} foi adicionado em sua conta no bot.</b>",
                reply_markup=kb,
            )

            user = User(id=objeto.user_id, first_name=name, username=username)
            mention = create_mention(user)
            insert_sold_balance(value, objeto.user_id, "auto")
            await c.send_message(
                ADMIN_CHAT,
                f"<b>💰 {mention} Adicionou <b>R${value}</b> de saldo</b>",
            )
            mention = user.first_name
            await c.send_message(
                GRUPO_PUB,
                f"<b>💰 {mention} Adicionou <b>R${value}</b> de saldo</b>",
            )

            """
            if refer:
                cur.execute(
                    "UPDATE users SET balance = round(balance + ?, 2) WHERE id = ?",
                    [refer_bonus, refer],
                )

                mention = create_mention(user, with_id=False)

                await c.send_message(
                    refer,
                    f'💸 Seu referenciado "{mention}" adicionou saldo no bot e você recebeu {refer_bonus} saldo.',
                )"""
            save()
            return

        await asyncio.sleep(2)

    if objeto.c in ["PagBank", "GerenciaNet"]:
        await objeto.hc.aclose()

    await send.edit_text(
        "<b>📛 Nenhum depósito foi feito em 5 minutos, adição de saldo cancelada.</b>",
        reply_markup=kb,
    )

    name, username = cur.execute(
        "SELECT name_user, username FROM users WHERE id = ?", [objeto.user_id]
    ).fetchone()
    user = User(id=objeto.user_id, first_name=name, username=username)
    mention = create_mention(user)

    txt_info_user = f"""<b>📛 Ops! O usuário: {mention}
<b>💰 solicitou pix automatico e não pagou.😕😱</b>
{get_support_user()}
"""
    return await c.send_message(ADMIN_CHAT, txt_info_user)


@Client.on_message(filters.command(["pix", "recarga", "saldo"]))
@Client.on_callback_query(filters.regex(r"^add_saldo_auto$"))
async def auto_pay(c: Client, m: Union[CallbackQuery, Message]):
    select_pay = cur.execute("SELECT pay_auto FROM bot_config").fetchone()[0]

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Voltar", callback_data="add_saldo")]
        ]
    )

    if not select_pay:
        if isinstance(m, CallbackQuery):
            return await m.answer(
                "⚠️ O Pix automático está desativado, por favor use o pix manual.",
                show_alert=True,
            )
        else:
            return m.reply_text(
                "⚠️ O Pix automático está desativado, por favor use o pix manual.",
                reply_markup=kb,
            )

    value = None

    min_value = 10
    max_value = 200
    if isinstance(m, CallbackQuery):
        await m.message.delete()

        cob = await m.message.ask(
            f"""<b>💎 Digite o valor que você quer depositar (mínimo R$ {min_value}), exemplo:

- 💠 15
- 💠 20
- 💠 25
- 💠 30

⚠️ Caso não consiga efetuar o pagamento, chame o 👉 {BOT_LINK_SUPORTE}
{details}""",
            filters=filters.regex(r"^\d+(\.\d{2})?$"),
            reply_markup=ForceReply(),
            timeout=120,
        )

        value = float(cob.text)

        if value < min_value:
            return await m.message.reply_text(
                f"<b>⚠️ O valor deve ser maior que {min_value}.</b>", reply_markup=kb
            )
        if value > max_value:
            return await m.message.reply_text(
                f"<b>⚠️ O valor deve ser menor que {max_value}.</b>", reply_markup=kb
            )
    elif isinstance(m, Message):
        if len(m.command) == 1:
            cob = await m.ask(
                f"""<b>💎 Digite o valor que você quer depositar (mínimo R$ {min_value}), exemplo:

- 💠 15
- 💠 20
- 💠 25
- 💠 30

⚠️ Caso não consiga efetuar o pagamento, chame o 👉 {BOT_LINK_SUPORTE}
{details}</b>""",
                filters=filters.regex(r"^\d+(\.\d{2})?$"),
                reply_markup=ForceReply(),
                timeout=120,
            )
            value = float(cob.text)
        else:
            value = float(re.search(r"(?P<valor>\d+)", m.command[1])["valor"])

        if value < min_value:
            return await m.reply_text(
                f"<b>⚠️ O valor deve ser maior que {min_value}.</b>", reply_markup=kb
            )
        if value > max_value:
            return await m.reply_text(
                f"<b>⚠️ O valor deve ser menor que {max_value}.</b>", reply_markup=kb
            )

    mm = m.message if isinstance(m, CallbackQuery) else m

    dados = cur.execute(
        "SELECT cpf, name, email FROM users  WHERE id = ?", [m.from_user.id]
    ).fetchone()

    pay_not_instance: Union[Gerencianet, MercadoPago, PagBank] = AUTO_PAYMENTS[
        select_pay
    ]

    pay, qr = "", ""

    '''
    if None in (dados[0], dados[2]) and select_pay == "mercado pago":
        cpf, full_name = "0", "0"
        await mm.reply_text(
            "Você não possui dados cadastrados, por favor responda o formulario a seguir.\n"
            "É importante que os dados forcecidos sejam <b>os mesmos do pagador</b> para verificar o pagamento, caso contrário o mesmo não será creditado.\n"
            'Caso precise alterar os dados posteriormente, use a opção "<b>Alterar dados Pix</b>", localizado em "<b>Suas informações</b>".',
        )
        await asyncio.sleep(1.5)
        email = await mm.ask("<b>📧 E-mail:</b>", reply_markup=ForceReply(), timeout=120)
        ativ = 0
        if ativ:
            full_name = await mm.ask(
                "<b>👤 Nome completo do pagador:</b>",
                reply_markup=ForceReply(),
                timeout=120,
            )
            full_name = full_name.text

        cpf = ""
        for _ in range(3):
            cpf = await mm.ask(
                "<b>👤 CPF da lara (válido) da lara que irá pagar:</b>",
                reply_markup=ForceReply(),
                timeout=120,
            )
            if cpf_validate(cpf.text):
                break

        if not cpf_validate(cpf.text):
            return

        cpf, full_name, email = (cpf.text, full_name, email.text)
        cur.execute(
            """UPDATE users SET cpf = ?, name = ?, email = ? WHERE id = ?""",
            [cpf, full_name, email, m.from_user.id],
        )
        save()

    else:
        cpf, full_name, email = dados
        if dados == None:
            cpf, full_name, email = 1, 1, 1'''

    cpf, full_name, email = 1, 1, 1

    if select_pay == "mercado pago":
        app_user = cur.execute(
            "SELECT client_secret FROM tokens WHERE type_token= ?", [select_pay]
        ).fetchone()[0]
        pay: Union[Gerencianet, MercadoPago] = pay_not_instance(acess_token=app_user)
        resp = await pay.create_payment(
            value=value,
            email=email,
            full_name=full_name,
            cpf=cpf,
            user_id=m.from_user.id,
        )
        qr = resp["copy_paste"]

    elif select_pay == "gerencia net":
        client_id, client_secret, name_cert_pem = cur.execute(
            "SELECT client_id, client_secret, name_cert_pem FROM tokens WHERE type_token= ?",
            [select_pay],
        ).fetchone()
        key = cur.execute("SELECT random_pix FROM bot_config").fetchone()[0]

        objeto = GerencianetCredentials(
            client_id=client_id,
            client_secret=client_secret,
            key=key,
            cert=name_cert_pem,
        )
        pay = pay_not_instance(objeto)
        resp = await pay.create_payment(
            value=value, time=330, cpf=cpf, name=full_name, user_id=m.from_user.id
        )
        qr = resp.get("qrcode")

    elif select_pay == "pagbank":
        client_id, client_secret, path_pem, path_key = cur.execute(
            "SELECT client_id, client_secret, name_cert_pem, name_cert_key FROM tokens WHERE type_token= ?",
            [select_pay],
        ).fetchone()

        key = cur.execute("SELECT random_pix_pb FROM bot_config").fetchone()[0]

        objeto = PagBankCredentials(client_id, client_secret, key, path_pem, path_key)

        await objeto.gerar_tk()

        pay = pay_not_instance(objeto)
        resp = await pay.create_payment(
            value=value, time=330, cpf=cpf, name=full_name, user_id=m.from_user.id
        )
        qr = resp["pixCopiaECola"]
    elif select_pay == "juno":
        client_id, client_secret, key_pix, priv_token = cur.execute(
            "SELECT client_id, client_secret, name_cert_key, bearer_tk FROM tokens WHERE type_token= ?",
            [select_pay],
        ).fetchone()
        objeto = JunoCredentials(client_id, client_secret, key_pix, priv_token)
        pay = Juno(objeto)
        qr = await pay.create_payment(value=value, user_id=m.from_user.id)
    else:
        return

    base = f"""<b>💰 valor do pix solicitado: </b><i> R$ {float(value)}</i>
<b>Pix copia e cola abaixo👇 (clique para copiar)</b>

<code>{qr}</code>


<b>😥 Se não conseguir fazer pix automático, chame o @URSOO011</b>
"""

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Voltar", callback_data="start"
                )
            ]
        ]
    )
    send = await mm.reply_text(base, reply_markup=kb)
    asyncio.create_task(verify_pay(objeto=pay, c=c, send=send, value=value))

