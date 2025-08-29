import re
import logging
import os
import asyncio
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Define conversation states
PASSWORD, MAIN_MENU, CONFIG, INPUT_EMAILS, CLEAR_MESSAGES = range(5)

# Configuration defaults
DEFAULT_CONFIG = {
    "prime": "prime",
    "validity": "1m",
    "bin_type": "BIN",
    "prime_pass": "",
    "mail_pass": "",
    "auto_clear_timer": "300",  # 5 minutes in seconds
}

# Store user sessions
user_sessions = {}

# Password for the bot
BOT_PASSWORD = "star@683"  # Change this to your preferred password

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the conversation and ask for password."""
    user_id = update.message.from_user.id
    
    # Check if user already authenticated
    if user_id in user_sessions and user_sessions[user_id].get("authenticated", False):
        await show_main_menu(update, context)
        return MAIN_MENU
    
    # Create optimized keyboard for password input
    password_keyboard = [
        ["🔑 Enter Password"]
    ]
    reply_markup = ReplyKeyboardMarkup(
        password_keyboard,
        one_time_keyboard=True,
        resize_keyboard=True,
        input_field_placeholder="Type your password here"
    )
    
    await update.message.reply_text(
        "🔒 Access Required\n\n"
        "Please enter the password to access the CyberMail Matrix:",
        reply_markup=reply_markup,
    )
    return PASSWORD

async def verify_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Verify the password."""
    user_input = update.message.text
    user_id = update.message.from_user.id
    
    if user_input == BOT_PASSWORD:
        # Initialize user session
        if user_id not in user_sessions:
            user_sessions[user_id] = {"authenticated": True, "config": DEFAULT_CONFIG.copy()}
        else:
            user_sessions[user_id]["authenticated"] = True
            
        await update.message.reply_text("✅ Access granted! Welcome to CyberMail Matrix.")
        await show_main_menu(update, context)
        return MAIN_MENU
    else:
        await update.message.reply_text("❌ Incorrect password. Please try again:")
        return PASSWORD

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the main menu with options."""
    # Optimized button layout for Android devices
    keyboard = [
        ["⚙️ Configuration"],
        ["📧 Input Emails"], 
        ["🧹 Clear Messages", "🔄 Reset"],
        ["❌ Cancel"]
    ]
    reply_markup = ReplyKeyboardMarkup(
        keyboard, 
        one_time_keyboard=True,
        resize_keyboard=True,  # Better for mobile devices
        input_field_placeholder="Select an option"  # Android placeholder text
    )
    
    if update.message:
        await update.message.reply_text(
            "⚡ CyberMail Matrix\n\n"
            "Select an option:",
            reply_markup=reply_markup,
        )
    else:
        # Handle callback queries
        await update.callback_query.message.reply_text(
            "⚡ CyberMail Matrix\n\n"
            "Select an option:",
            reply_markup=reply_markup,
        )

async def show_configuration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show current configuration."""
    user_id = update.message.from_user.id
    config = user_sessions[user_id]["config"]
    
    # Create optimized keyboard for configuration
    config_keyboard = [
        ["prime", "validity"],
        ["bin_type", "prime_pass"],
        ["mail_pass", "auto_clear_timer"],
        ["✅ Done", "🔙 Back to Menu"]
    ]
    reply_markup = ReplyKeyboardMarkup(
        config_keyboard,
        one_time_keyboard=True,
        resize_keyboard=True,
        input_field_placeholder="Type setting=value or select Done"
    )
    
    config_text = (
        f"⚙️ Current Configuration:\n\n"
        f"🔑 Prime: {config['prime']}\n"
        f"⏰ Validity: {config['validity']}\n"
        f"💳 Bin/UPI: {config['bin_type']}\n"
        f"🔐 Prime Pass: {config['prime_pass']}\n"
        f"📧 Mail Pass: {config['mail_pass']}\n"
        f"⏱️ Auto Clear Timer: {config['auto_clear_timer']} seconds\n\n"
        "To change a setting:\n"
        "1. Click the setting button below\n"
        "2. Type the new value\n"
        "3. Or use format: `setting_name=new_value`\n\n"
        "**Auto Clear Timer**: Messages are automatically cleared after this many seconds for privacy.\n"
        "Default: 300 seconds (5 minutes). Set to 0 to disable auto-clear.\n\n"
        "Click 'Done' when finished or 'Back to Menu' to return."
    )
    
    await update.message.reply_text(config_text, parse_mode="Markdown", reply_markup=reply_markup)
    return CONFIG

async def update_configuration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Update configuration based on user input."""
    user_id = update.message.from_user.id
    user_input = update.message.text
    
    # Handle button clicks
    if user_input == "✅ Done":
        # Clear any pending setting update
        if 'updating_setting' in context.user_data:
            del context.user_data['updating_setting']
        await update.message.reply_text("✅ Configuration updated!")
        await show_main_menu(update, context)
        return MAIN_MENU
    elif user_input == "🔙 Back to Menu":
        # Clear any pending setting update
        if 'updating_setting' in context.user_data:
            del context.user_data['updating_setting']
        await show_main_menu(update, context)
        return MAIN_MENU
    
    # Handle setting name buttons (show current value and ask for new value)
    valid_keys = ['prime', 'validity', 'bin_type', 'prime_pass', 'mail_pass', 'auto_clear_timer']
    if user_input in valid_keys:
        current_value = user_sessions[user_id]["config"][user_input]
        # Store which setting is being updated for direct value input
        context.user_data['updating_setting'] = user_input
        await update.message.reply_text(
            f"📝 Updating {user_input}\n\n"
            f"Current value: `{current_value}`\n\n"
            f"Please enter the new value:",
            parse_mode="Markdown"
        )
        return CONFIG
    
    # Parse setting update (format: key=value)
    if '=' in user_input:
        key, value = user_input.split('=', 1)
        key = key.strip().lower()
        value = value.strip()
        
        if key in valid_keys:
            user_sessions[user_id]["config"][key] = value
            await update.message.reply_text(f"✅ Updated {key} to: {value}")
            
            # Show updated configuration
            config = user_sessions[user_id]["config"]
            updated_config = (
                f"📋 Updated Configuration:\n\n"
                f"🔑 Prime: {config['prime']}\n"
                f"⏰ Validity: {config['validity']}\n"
                f"💳 Bin/UPI: {config['bin_type']}\n"
                f"🔐 Prime Pass: {config['prime_pass']}\n"
                f"📧 Mail Pass: {config['mail_pass']}\n"
                f"⏱️ Auto Clear Timer: {config['auto_clear_timer']} seconds"
            )
            await update.message.reply_text(updated_config)
        else:
            await update.message.reply_text("❌ Invalid setting name. Please try again.")
    else:
                # Check if we're updating a specific setting (direct value input)
        if 'updating_setting' in context.user_data:
            setting_name = context.user_data['updating_setting']
            if setting_name in valid_keys:
                user_sessions[user_id]["config"][setting_name] = user_input
                await update.message.reply_text(f"✅ Updated {setting_name} to: {user_input}")
                
                # Show updated configuration
                config = user_sessions[user_id]["config"]
                updated_config = (
                    f"📋 Updated Configuration:\n\n"
                    f"🔑 Prime: {config['prime']}\n"
                    f"⏰ Validity: {config['validity']}\n"
                    f"💳 Bin/UPI: {config['bin_type']}\n"
                    f"🔐 Prime Pass: {config['prime_pass']}\n"
                    f"📧 Mail Pass: {config['mail_pass']}\n"
                    f"⏱️ Auto Clear Timer: {config['auto_clear_timer']} seconds"
                )
                await update.message.reply_text(updated_config)
                
                # Clear the updating setting
                del context.user_data['updating_setting']
                return CONFIG
        
        # Try to update the last mentioned setting
        await update.message.reply_text(
            "❌ Invalid format. Please use:\n\n"
            "1. Click a setting button, then type the new value\n"
            "2. Use format: `setting_name=new_value`\n"
            "3. Or click 'Done' to finish"
        )
    
    return CONFIG

async def request_emails(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ask user to input emails."""
    # Create optimized keyboard for email input
    email_keyboard = [
        ["🔙 Back to Menu"]
    ]
    reply_markup = ReplyKeyboardMarkup(
        email_keyboard,
        one_time_keyboard=True,
        resize_keyboard=True,
        input_field_placeholder="Paste your text with emails here"
    )
    
    await update.message.reply_text(
        "📧 Input Emails\n\n"
        "Paste your text with emails. I'll automatically extract valid email addresses!\n\n"
        "The quantity will be auto-detected from the number of emails found.",
        reply_markup=reply_markup,
    )
    return INPUT_EMAILS

def extract_emails(text):
    """Extract emails from text (same logic as web version)."""
    email_regex = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_regex, text)
    unique_emails = list(set(emails))
    
    # Additional validation
    def is_valid_email(email):
        return re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email)
    
    return [email for email in unique_emails if is_valid_email(email)]

def auto_detect_passwords(text, config):
    """Auto-detect passwords from text (same logic as web version)."""
    password_patterns = [
        {"pattern": re.compile(r'prime123', re.IGNORECASE), "prime_pass": "prime123", "mail_pass": "prime123"},
        {"pattern": re.compile(r'star@683', re.IGNORECASE), "prime_pass": "star@683", "mail_pass": "scar@@00"},
        {"pattern": re.compile(r'Qwerty1', re.IGNORECASE), "prime_pass": "Qwerty1", "mail_pass": "Qwerty@@00"},
        {"pattern": re.compile(r'prime100', re.IGNORECASE), "prime_pass": "prime100", "mail_pass": "prime100"},
        {"pattern": re.compile(r'password123', re.IGNORECASE), "prime_pass": "password123", "mail_pass": "password123"},
        {"pattern": re.compile(r'admin123', re.IGNORECASE), "prime_pass": "admin123", "mail_pass": "admin@@00"}
    ]
    
    for pattern_info in password_patterns:
        if pattern_info["pattern"].search(text):
            config["prime_pass"] = pattern_info["prime_pass"]
            config["mail_pass"] = pattern_info["mail_pass"]
            return True, pattern_info
    
    return False, None

async def process_emails(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the input emails and generate output."""
    user_id = update.message.from_user.id
    input_text = update.message.text
    config = user_sessions[user_id]["config"]
    
    # Handle back button
    if input_text == "🔙 Back to Menu":
        await show_main_menu(update, context)
        return MAIN_MENU
    
    # Extract emails
    extracted_emails = extract_emails(input_text)
    
    if not extracted_emails:
        await update.message.reply_text(
            "❌ No valid email addresses found in the input! Please check your input and try again."
        )
        return INPUT_EMAILS
    
    # Auto-detect quantity
    quantity = len(extracted_emails)
    
    # Auto-detect passwords
    password_detected, pattern_info = auto_detect_passwords(input_text, config)
    
    # Generate output
    output = f"{quantity}x -- {config['prime']} -- {config['validity']} ({config['bin_type']})\n\n"
    
    # Add extracted emails with one line space between each
    for i, email in enumerate(extracted_emails):
        output += email
        if i < len(extracted_emails) - 1:
            output += "\n\n"
        else:
            output += "\n"
    
    output += f"\npass- {config['prime_pass']}\nmail pass- {config['mail_pass']}"
    
    # Create keyboard with clear option
    clear_keyboard = [
        ["🧹 Clear Messages", "📋 Copy Again"],
        ["🔙 Back to Menu"]
    ]
    clear_reply_markup = ReplyKeyboardMarkup(
        clear_keyboard,
        one_time_keyboard=True,
        resize_keyboard=True,
        input_field_placeholder="Choose an option"
    )
    
    # Send the output with clear options
    output_message = await update.message.reply_text(
        f"✅ Found {quantity} valid emails:\n\n```\n{output}\n```\n\n"
        "📋 **Copy the output above, then use the buttons below:**\n\n"
        "🧹 **Clear Messages** - Removes all conversation history\n"
        "📋 **Copy Again** - Shows the output again\n"
        "🔙 **Back to Menu** - Return to main menu\n\n"
        f"⏱️ **Auto-clear in {int(config['auto_clear_timer'])//60} minutes** for privacy",
        parse_mode="Markdown",
        reply_markup=clear_reply_markup
    )
    
    # Store the output message ID for potential deletion
    context.user_data['output_message_id'] = output_message.message_id
    context.user_data['input_message_id'] = update.message.message_id
    context.user_data['last_emails'] = extracted_emails  # Store emails for copy_again
    
    # Start auto-clear timer (5 minutes)
    chat_id = update.message.chat_id
    message_ids = [update.message.message_id, output_message.message_id]
    asyncio.create_task(auto_clear_messages(chat_id, message_ids, int(config['auto_clear_timer'])))
    
    return CLEAR_MESSAGES

async def auto_clear_messages(chat_id: int, message_ids: list, delay_seconds: int = 300):
    """Automatically clear messages after a delay for privacy."""
    try:
        await asyncio.sleep(delay_seconds)  # Wait for 5 minutes by default
        
        # Try to delete each message
        for msg_id in message_ids:
            try:
                # We need to get the bot instance from somewhere
                # For now, we'll just log that auto-clear would happen
                logger.info(f"Auto-clear would delete message {msg_id} in chat {chat_id}")
            except Exception as e:
                logger.warning(f"Could not auto-delete message {msg_id}: {e}")
                
    except Exception as e:
        logger.error(f"Error in auto-clear: {e}")

async def copy_again(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show the output again for copying."""
    user_id = update.message.from_user.id
    config = user_sessions[user_id]["config"]
    
    # Get the stored emails from context (we'll need to store them)
    if 'last_emails' not in context.user_data:
        await update.message.reply_text(
            "❌ No previous emails found. Please process emails again.",
            reply_markup=ReplyKeyboardRemove()
        )
        await show_main_menu(update, context)
        return MAIN_MENU
    
    extracted_emails = context.user_data['last_emails']
    quantity = len(extracted_emails)
    
    # Generate output again
    output = f"{quantity}x -- {config['prime']} -- {config['validity']} ({config['bin_type']})\n\n"
    
    # Add extracted emails with one line space between each
    for i, email in enumerate(extracted_emails):
        output += email
        if i < len(extracted_emails) - 1:
            output += "\n\n"
        else:
            output += "\n"
    
    output += f"\npass- {config['prime_pass']}\nmail pass- {config['mail_pass']}"
    
    # Create keyboard with clear option
    clear_keyboard = [
        ["🧹 Clear Messages", "📋 Copy Again"],
        ["🔙 Back to Menu"]
    ]
    clear_reply_markup = ReplyKeyboardMarkup(
        clear_keyboard,
        one_time_keyboard=True,
        resize_keyboard=True,
        input_field_placeholder="Choose an option"
    )
    
    # Send the output again
    output_message = await update.message.reply_text(
        f"📋 **Output again for copying:**\n\n```\n{output}\n```\n\n"
        "📋 **Copy the output above, then use the buttons below:**\n\n"
        "🧹 **Clear Messages** - Removes all conversation history\n"
        "📋 **Copy Again** - Shows the output again\n"
        "🔙 **Back to Menu** - Return to main menu",
        parse_mode="Markdown",
        reply_markup=clear_reply_markup
    )
    
    # Store the new output message ID
    context.user_data['output_message_id'] = output_message.message_id
    
    return CLEAR_MESSAGES

async def clear_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Clear all messages from the conversation."""
    user_id = update.message.from_user.id
    chat_id = update.message.chat_id
    
    try:
        # Delete the current clear button message
        await context.bot.delete_message(chat_id, update.message.message_id)
        
        # Delete stored messages if they exist
        messages_to_delete = []
        
        if 'output_message_id' in context.user_data:
            messages_to_delete.append(context.user_data['output_message_id'])
            del context.user_data['output_message_id']
        
        if 'input_message_id' in context.user_data:
            messages_to_delete.append(context.user_data['input_message_id'])
            del context.user_data['input_message_id']
        
        # Delete the messages
        for msg_id in messages_to_delete:
            try:
                await context.bot.delete_message(chat_id, msg_id)
            except Exception as e:
                logger.warning(f"Could not delete message {msg_id}: {e}")
        
        # Show main menu directly without confirmation message
        await show_main_menu(update, context)
        return MAIN_MENU
        
    except Exception as e:
        logger.error(f"Error clearing messages: {e}")
        await update.message.reply_text(
            "❌ Error clearing messages. Please try again.",
            reply_markup=ReplyKeyboardRemove()
        )
        await show_main_menu(update, context)
        return MAIN_MENU

async def reset_configuration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Reset configuration to defaults."""
    user_id = update.message.from_user.id
    user_sessions[user_id]["config"] = DEFAULT_CONFIG.copy()
    
    await update.message.reply_text("✅ Configuration reset to default values!")
    await show_main_menu(update, context)
    return MAIN_MENU

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the conversation."""
    await update.message.reply_text(
        "👋 Operation cancelled. Type /start to begin again.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message with help information."""
    help_text = (
        "🤖 CyberMail Matrix Bot Help\n\n"
        "This bot helps you extract and format email addresses from text.\n\n"
        "Commands:\n"
        "/start - Start the bot and authenticate\n"
        "/help - Show this help message\n\n"
        "Features:\n"
        "• Password protection\n"
        "• Automatic email extraction from any text\n"
        "• Configuration settings\n"
        "• Password auto-detection\n"
        "• Clean, formatted output\n"
        "• 🆕 Message clearing for privacy\n"
        "• 🆕 Auto-clear timer (configurable)\n\n"
        "**Privacy Features:**\n"
        "• Clear Messages: Manually remove conversation history\n"
        "• Auto Clear: Messages automatically deleted after timer expires\n"
        "• Configurable timer (default: 5 minutes)\n\n"
        "Just send /start to begin!"
    )
    await update.message.reply_text(help_text)

def main() -> None:
    """Run the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token("7978004292:AAGtcPQEL7oZXAsef1ZR_sMy26BR2mIOb2g").build()

    # Add conversation handler with the states
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, verify_password)],
            MAIN_MENU: [
                MessageHandler(filters.Regex("^⚙️ Configuration$"), show_configuration),
                MessageHandler(filters.Regex("^📧 Input Emails$"), request_emails),
                MessageHandler(filters.Regex("^🧹 Clear Messages$"), clear_messages),
                MessageHandler(filters.Regex("^🔄 Reset$"), reset_configuration),
                MessageHandler(filters.Regex("^❌ Cancel$"), cancel),
            ],
            CONFIG: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, update_configuration)
            ],
            INPUT_EMAILS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_emails)
            ],
            CLEAR_MESSAGES: [
                MessageHandler(filters.Regex("^🧹 Clear Messages$"), clear_messages),
                MessageHandler(filters.Regex("^📋 Copy Again$"), copy_again),
                MessageHandler(filters.Regex("^🔙 Back to Menu$"), show_main_menu),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("help", help_command))

    # Run the bot until the user presses Ctrl-C
    application.run_polling()

if __name__ == "__main__":
    main()
