from .base import Command
import time
import datetime


class ExportChatCommand(Command):
    """Export chat history to a text file."""
    command_name = "/export"
    aliases = ["export"]

    async def execute(self):
        peer_id = self.event.message.peer_id
        progress = await self.client_handler.send_message(peer_id, "Starting export...")
        try:
            text = await self._collect_messages(peer_id, progress)
            await self.client_handler.edit_message(peer_id, progress.id, "Sending export...")
            await self.client_handler.send_text_as_file(peer_id, text, "chat_export.txt", reply_to=self.event.message.id)
        finally:
            await self.client_handler.delete_message(peer_id, progress.id)
            await self.client_handler.delete_message(peer_id, self.event.message.id)

    async def _collect_messages(self, peer_id, progress_message):
        client = self.client_handler.client
        total = (await client.get_messages(peer_id, limit=0)).total
        count = 0
        last_update = time.time()
        current_day = None
        lines = []
        async for msg in client.iter_messages(peer_id, reverse=True):
            count += 1
            if msg.text and not msg.text.startswith(self.command_name):
                date = msg.date.astimezone()
                day = date.strftime('%Y-%m-%d')
                if day != current_day:
                    lines.append(f"\n{day}\n")
                    current_day = day
                sender = await msg.get_sender()
                name_parts = []
                if getattr(sender, 'first_name', None):
                    name_parts.append(sender.first_name)
                if getattr(sender, 'last_name', None):
                    name_parts.append(sender.last_name)
                name = ' '.join(name_parts)
                username = f"@{sender.username}" if getattr(sender, 'username', None) else ''
                header = f"{name} [{username}] - {date.strftime('%H:%M')}" if username else f"{name} - {date.strftime('%H:%M')}"
                lines.append(header)
                lines.append(msg.text)
                lines.append("")
            now = time.time()
            if now - last_update >= 5:
                percent = count / total * 100 if total else 0
                bar = self._progress_bar(percent)
                await self.client_handler.edit_message(peer_id, progress_message.id,
                                                       f"Exporting {bar} {percent:.1f}% ({count}/{total})")
                last_update = now
        return "\n".join(lines)

    @staticmethod
    def _progress_bar(percent, length=20):
        filled = int(length * percent / 100)
        return '[' + '=' * filled + ' ' * (length - filled) + ']'
