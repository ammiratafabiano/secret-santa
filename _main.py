import time
from random import shuffle
import traceback
from telegram import Update, ReplyKeyboardRemove, helpers, InlineKeyboardButton, InlineKeyboardMarkup
import logging

from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ConversationHandler, \
    PicklePersistence, ContextTypes
from costants import BOT_TOKEN, ADMIN_ID
from utils import format_name, write_log

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

POLLING, BO = range(2)
START, SKIP, READY, RESULT = range(4)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    my_chat_id = str(update.effective_chat.id)
    add_user_report(context, my_chat_id)
    if 'groups' not in context.bot_data:
        context.bot_data['groups'] = []
    current_group = []
    current_user = None
    for group in context.bot_data['groups']:
        for user in group:
            if user[0] == my_chat_id:
                current_group = group
                current_user = user
    sent_group = []
    if context.args:
        for group in context.bot_data['groups']:
            for user in group:
                if user[0] == context.args[0]:
                    sent_group = group
    if sent_group and current_group and sent_group != current_group:
        text = 'Sei già dentro un altro grupo\\.\n\nClicca /cancel per uscire dal gruppo corrente, poi clicca nuovamente sul link di invito per entrare su quello nuovo\\.'
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)
        return POLLING
    elif sent_group:
        current_group = sent_group

    if not current_user:
        text = get_info_text()
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)

    text, reply_markup = get_new_message_data(update, context, current_group=current_group, current_user=current_user)

    if query:
        await query.answer()
        try:
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN_V2, disable_web_page_preview=True,
                                          reply_markup=reply_markup)
        except (ValueError, Exception):
            print(traceback.format_exc())
            logging.error(f'Problem editing message.')
    else:
        if current_user and current_user[1]:
            try:
                await context.bot.delete_message(current_user[0], current_user[1])
            except (ValueError, Exception):
                print(traceback.format_exc())
                logging.error(f'Problem deleting message.')
            try:
                await update.message.delete()
            except (ValueError, Exception):
                print(traceback.format_exc())
                logging.error(f'Problem deleting message.')

        message = await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2, disable_web_page_preview=True,
                                                  reply_markup=reply_markup)
        for group in context.bot_data['groups']:
            for user in group:
                if user[0] == my_chat_id:
                    user[1] = message.message_id

        if not current_user:
            my_name = format_name(update.effective_user.username, update.effective_user.first_name,
                                  update.effective_user.last_name)
            current_user = [my_chat_id, message.message_id, my_name, [my_chat_id], False, None, '']
            current_group = [*current_group, current_user]
            found = False
            for i, group in enumerate(context.bot_data['groups']):
                for user in group:
                    for u in current_group:
                        if user[0] == u[0]:
                            context.bot_data['groups'][i] = current_group
                            found = True
                    if found:
                        break
                if found:
                    break
            if not found:
                context.bot_data['groups'].append(current_group)
    try:
        for user in current_group:
            if user[0] != my_chat_id:
                text, reply_markup = get_new_message_data(update, context, chat_id=user[0])
                await context.bot.edit_message_text(chat_id=user[0], message_id=user[1], text=text,
                                                    parse_mode=ParseMode.MARKDOWN_V2, disable_web_page_preview=True,
                                                    reply_markup=reply_markup)
    except (ValueError, Exception):
        print(traceback.format_exc())
        logging.error(f'Problem sending update to users.')
    return POLLING


async def toggle_skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        current_user, current_group = get_user(update, context)
        if not current_user[4]:
            chat_id = query.data.split()[1]
            if chat_id != current_user[0]:
                blocked = 0
                for group in context.bot_data['groups']:
                    for user in group:
                        if current_user[0] in user[3]:
                            blocked += 1
                for group in context.bot_data['groups']:
                    for user in group:
                        if user[0] == chat_id:
                            if current_user[0] in user[3]:
                                user[3].remove(current_user[0])
                            elif blocked == len(group) - 1:
                                await query.answer('Non puoi non avere un Babbo Natale segreto.')
                                return POLLING
                            else:
                                await query.answer(
                                    'Fatto. Sarà poi comunicato a tutti.')
                                user[3].append(current_user[0])

                return await start(update, context)
            else:
                await query.answer('Non puoi essere il Babbo Natale segreto di te stesso.')
                return POLLING
        else:
            await query.answer('Togli la conferma per modificare.')
            return POLLING
    else:
        return ConversationHandler.END


async def toggle_ready(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    my_chat_id = str(update.effective_chat.id)
    if query:
        for group in context.bot_data['groups']:
            for user in group:
                if user[0] == my_chat_id:
                    user[4] = not user[4]
        return await start(update, context)
    else:
        return ConversationHandler.END


async def calculate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    current_user, current_group = get_user(update, context)
    if query:
        users = []
        timeout = time.time() + 10
        while True:
            if time.time() > timeout:
                logging.error(f'Too much conditions or timeout.')
                await query.answer('Sono state messe troppe condizioni.')
                return POLLING
            for user in current_group:
                users.append(user[0])
            shuffle_users = users.copy()
            shuffle(shuffle_users)
            error = False
            for i, user in enumerate(current_group):
                if user[0] == users[i] and shuffle_users[i] in user[3]:
                    error = True
            if not error:
                break
            else:
                users = []
        log = ''
        log2 = ''
        conditions_text = get_conditions_text(update, context)

        for i, user in enumerate(current_group):
            if users[i] == user[0]:
                result_user, result_group = get_user(update, context, str(shuffle_users[i]))
                log += f'{user[0]} -> {result_user[0]} (excluded {user[3]})\n'
                log2 += f'{user[2]} -> {result_user[2]}\n'
                user[5] = result_user[2]
                user[6] = conditions_text
        log2 += f'\n\n{conditions_text}'
        write_log(str(update.effective_chat.id), log)
        write_log(str(update.effective_chat.id) + '_spoilers', log2)
        add_group_completed_report(context)
        return await start(update, context)
    return ConversationHandler.END


async def result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        user, group = get_user(update, context)
        if user[5]:
            await query.answer()
            await query.edit_message_text(f'*Risultato dell\'estrazione*\n\n||{user[5]}||{user[6] if user[6] else ""}',
                                          parse_mode=ParseMode.MARKDOWN_V2)
            await remove_current(update, context)
            return ConversationHandler.END
        else:
            await query.answer('Si è verificato un problema.')
            return ConversationHandler.END
    else:
        return ConversationHandler.END


async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id == ADMIN_ID:
        return await report(update, context)
    text = get_info_text()
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)
    return ConversationHandler.END


async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        n_users = len(context.bot_data['users']) if 'users' in context.bot_data else 0
        n_groups = len(context.bot_data['groups']) if 'groups' in context.bot_data else 0
        n_completed_groups = context.bot_data['n_completed_groups'] if 'n_completed_groups' in context.bot_data else 0
        text = f'*Riepilogo bot*\n\nVisitatori: {n_users}\nGruppi correnti: {n_groups}\nGruppi completati: {n_completed_groups}'
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)
        return ConversationHandler.END
    except (ValueError, Exception):
        print(traceback.format_exc())
        logging.error(f'Problem in report.')


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await remove_current(update, context, send_update=True)
    text = 'Operazioni in corso annullate.'
    await update.message.reply_text(text, reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


async def no_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = 'Niente da annullare'
    await update.message.reply_text(text, reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


async def remove_current(update: Update, context: ContextTypes.DEFAULT_TYPE, send_update=False):
    current_user, group = get_user(update, context)
    group.remove(current_user)
    if len(group) == 0:
        context.bot_data['groups'].remove(group)
    if send_update:
        try:
            for user in group:
                if user[0] != current_user[0]:
                    text, reply_markup = get_new_message_data(update, context, chat_id=user[0])
                    await context.bot.edit_message_text(chat_id=user[0], message_id=user[1], text=text,
                                                        parse_mode=ParseMode.MARKDOWN_V2, disable_web_page_preview=True,
                                                        reply_markup=reply_markup)
        except (ValueError, Exception):
            print(traceback.format_exc())
            logging.error(f'Problem removing users after result.')


def get_user(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id=None):
    if not chat_id:
        chat_id = str(update.effective_chat.id)
    if 'groups' not in context.bot_data:
        context.bot_data['groups'] = []
    for group in context.bot_data['groups']:
        for user in group:
            if user[0] == chat_id:
                return user, group
    return None, None


def get_new_message_data(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id=None, current_group=None,
                         current_user=None):
    if not chat_id:
        chat_id = str(update.effective_chat.id)

    if not current_group:
        for group in context.bot_data['groups']:
            for user in group:
                if user[0] == chat_id:
                    current_group = group
                    current_user = user

    conditions_warning = ''
    url = helpers.create_deep_linked_url(context.bot.username, chat_id)
    my_name = format_name(update.effective_user.username, update.effective_user.first_name,
                          update.effective_user.last_name)

    text = ''
    reply_markup = []
    if current_user and current_user[5]:
        text = f'*Estrazione Pronta\\!*'
        reply_markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=u'\U0001F381 Vai all\'estrazione', callback_data=str(RESULT))]
        ])
    else:
        buttons = []
        all_ready = True
        for user in current_group:
            confirmed = u'\U0001F197 ' if user[4] else ''
            disabled = u' \U0001F6AB' if chat_id in user[3] else ''
            label = f'{confirmed}{user[2]}{disabled}'
            if user[0] == chat_id:
                buttons.append([InlineKeyboardButton(text=label, callback_data=str(READY))])
            else:
                buttons.append([InlineKeyboardButton(text=label, callback_data=str(SKIP) + ' ' + user[0])])
            all_ready = False if not user[4] else all_ready
        if not current_user:
            buttons.append(
                [InlineKeyboardButton(text=my_name + u' \U0001F6AB', callback_data=str(READY))])
            all_ready = False
        if all_ready:
            conditions_warning = get_conditions_warning(update, context)
        if len(current_group) > 1 and current_group[0][0] == chat_id and all_ready and not conditions_warning:
            buttons.append([InlineKeyboardButton(text=u'\U000025B6 Inizia estrazione', callback_data=str(START))])
        reply_markup = InlineKeyboardMarkup(inline_keyboard=buttons)
        text = f'*Sala di attesa*\n\n[LINK DI INVITO]({url}){conditions_warning}'

    return text, reply_markup


def get_conditions_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conditions_text = ''
    user, group = get_user(update, context)
    condition_list = []
    for u in group:
        conditions = []
        for blocked in u[3]:
            if blocked != u[0]:
                blocked_user, blocked_group = get_user(update, context, blocked)
                conditions.append(blocked_user[2])
        if conditions:
            conditions_users = ', '.join(conditions)
            condition_list.append(f'{u[2]} non può essere il Babbo Natale segreto di {conditions_users}')
    if condition_list:
        conditions_list_text = '\n\n'.join(condition_list)
        conditions_text = f'\n\n\nControllare che le seguenti condizioni inserite dai partecipanti siano corrette:\n\n{conditions_list_text}'
    return conditions_text


def get_conditions_warning(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user, group = get_user(update, context)
    warning_list_text = ''
    warning_list = []
    for u in group:
        if len(group) - len(u[3]) == 0:
            warning_list.append(f'{u[2]} non può essere il Babbo Natale segreto di nessuno\\.')
    if warning_list:
        warning_list_text = f'\n\n\nProblemi con le condizioni messe:\n\n' + '\n\n'.join(warning_list)
    return warning_list_text


def get_info_text():
    text = 'Ciao\\! Ecco alcune informazioni utili\\:\n\n🔗 Tieni premuto il link di invito così da mandarlo a chi vuoi che venga aggiunto ' \
           'alla lista\n\n🚫 Se c\'è una condizione per la quale una persona non può essere il tuo Babbo Natale segreto clicca su di essa\\.\n\n' \
           '🆗 Se hai finito di controllare le condizioni di estrazione clicca sul tuo nome per comunicarlo agli altri\\.\n\n' \
           '▶️ Se sei l’admin e se tutti i partecipanti sono pronti clicca “Inizia estrazione” per iniziare l’estrazione\\.\n\n' \
           '🎁 Quando l’admin avrà effettuato l’estrazione premi il tasto “Vai all’estrazione” per vedere il risultato\\.'
    return text


def add_user_report(context, user_id):
    try:
        if 'users' in context.bot_data:
            if user_id not in context.bot_data['users']:
                context.bot_data['users'] = [*context.bot_data['users'], user_id]
        else:
            context.bot_data['users'] = [user_id]
    except (ValueError, Exception):
        print(traceback.format_exc())
        logging.error(f'Problem adding user report.')


def add_group_completed_report(context):
    try:
        if 'n_completed_groups' in context.bot_data:
            context.bot_data['n_completed_groups'] += 1
        else:
            context.bot_data['n_completed_groups'] = 1
    except (ValueError, Exception):
        print(traceback.format_exc())
        logging.error(f'Problem adding group report.')


if __name__ == '__main__':
    persistence = PicklePersistence(filepath='conversationbot')
    app = ApplicationBuilder().token(BOT_TOKEN).persistence(persistence).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            POLLING: [
                CommandHandler('cancel', cancel),
                CallbackQueryHandler(toggle_ready, pattern='^' + str(READY) + '$'),
                CallbackQueryHandler(toggle_skip, pattern='^' + str(SKIP) + ' '),
                CallbackQueryHandler(result, pattern='^' + str(RESULT) + '$'),
                CallbackQueryHandler(calculate, pattern='^' + str(START) + '$')
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        name="addwatch_conversation",
        persistent=True,
        allow_reentry=True
    )
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler('cancel', no_cancel))
    app.add_handler(CommandHandler("info", info))
    app.run_polling()
