# DIP-0020: WhatsApp Module

> **Status**: Draft
> **Author**: Gregor
> **Created**: 2026-01-28
> **Related**: DIP-0010 (External Sync), DIP-0012 (CRM Module)

## Summary

Native WhatsApp integration for Datacore providing:
1. **CRM Adapter** - Import contacts and track interactions from WhatsApp
2. **Bidirectional Gateway** - Send/receive messages, run Datacore commands via WhatsApp
3. **Proactive Notifications** - Morning briefings, follow-up reminders pushed to WhatsApp

## Motivation

WhatsApp is the primary messaging channel for many professional contacts. Current options:
- Manual chat exports (tedious, no automation)
- Moltbot (security risks, knowledge fragmentation)
- No native Datacore integration

A native module keeps all data in Datacore, follows existing patterns, and maintains single source of truth.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Datacore WhatsApp Module                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │  Export      │    │  WhatsApp    │    │  Message     │       │
│  │  Parser      │    │  Adapter     │    │  Handler     │       │
│  │  (CRM)       │    │  (CRM)       │    │  (Gateway)   │       │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘       │
│         │                   │                   │                │
│         └───────────────────┼───────────────────┘                │
│                             │                                    │
│                    ┌────────▼────────┐                          │
│                    │   WAHA Gateway  │                          │
│                    │   (HTTP API)    │                          │
│                    └────────┬────────┘                          │
│                             │                                    │
└─────────────────────────────┼────────────────────────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │   WhatsApp Web    │
                    │   (your phone)    │
                    └───────────────────┘
```

## Components

### 1. WAHA Gateway (External)

**[WAHA](https://waha.devlike.pro/)** - Self-hosted WhatsApp HTTP API

Why WAHA over alternatives:
- Python-friendly REST API
- Docker deployment
- Session management
- Webhook support for incoming messages
- Active maintenance
- No Node.js in Datacore codebase

```bash
# Start WAHA
docker run -d \
  --name waha \
  -p 3000:3000 \
  -v ./waha-data:/app/.sessions \
  devlikeapro/waha
```

### 2. WhatsApp Export Parser

Parse manual `.txt` exports for initial contact import.

**File:** `lib/whatsapp_export_parser.py`

```python
class WhatsAppExportParser:
    """Parse WhatsApp chat export files."""

    # iOS format: [DD/MM/YYYY, HH:MM:SS] Name: Message
    IOS_PATTERN = re.compile(
        r'\[(\d{2}/\d{2}/\d{4}), (\d{2}:\d{2}:\d{2})\] ([^:]+): (.+)'
    )

    # Android format: DD/MM/YYYY, HH:MM - Name: Message
    ANDROID_PATTERN = re.compile(
        r'(\d{2}/\d{2}/\d{4}), (\d{2}:\d{2}) - ([^:]+): (.+)'
    )

    def parse_export(self, file_path: Path) -> ChatExport:
        """Parse export file into structured data."""

    def detect_format(self, content: str) -> str:
        """Detect iOS vs Android format."""

    def extract_participants(self, messages: List) -> List[str]:
        """Extract unique participants from messages."""
```

### 3. WhatsApp CRM Adapter

Following `CRMAdapter` pattern from DIP-0012.

**File:** `lib/whatsapp_adapter.py`

```python
class WhatsAppAdapter(CRMAdapter):
    """Extract interactions from WhatsApp."""

    adapter_type = "whatsapp"

    def __init__(self, data_root: Path, waha_url: str = "http://localhost:3000"):
        self.data_root = data_root
        self.waha_url = waha_url
        self.exports_dir = data_root / '.datacore' / 'state' / 'whatsapp' / 'exports'

    def extract_interactions(self, since: datetime, until: datetime = None) -> List[Interaction]:
        """
        Extract interactions from:
        1. Parsed export files
        2. WAHA API (if connected)
        """

    def resolve_contact(self, phone_or_name: str) -> Optional[str]:
        """
        Resolve phone number to contact name.
        Checks contacts/*.md for matching phone in channels.whatsapp
        """
```

### 4. Contact Creator

Create CRM contacts from WhatsApp data.

**File:** `lib/whatsapp_contact_creator.py`

```python
class WhatsAppContactCreator:
    """Create CRM contacts from WhatsApp exports/chats."""

    def create_contacts_from_export(self, export_path: Path, space: str) -> List[Path]:
        """Parse export and create draft contacts."""

    def sync_from_waha(self, space: str) -> List[Path]:
        """Sync contacts from WAHA gateway."""

    def match_existing_contact(self, phone: str, name: str) -> Optional[Path]:
        """Find existing contact by phone or fuzzy name match."""
```

### 5. Message Handler (Gateway)

Handle incoming messages and route to Datacore commands.

**File:** `lib/whatsapp_gateway.py`

```python
class WhatsAppGateway:
    """Bidirectional WhatsApp gateway for Datacore."""

    def __init__(self, waha_url: str, allowed_numbers: List[str]):
        self.waha = WAHAClient(waha_url)
        self.allowed = allowed_numbers

    async def on_message(self, message: IncomingMessage):
        """Handle incoming WhatsApp message."""
        if message.sender not in self.allowed:
            return  # Ignore unauthorized

        # Parse command
        command = self.parse_command(message.text)

        if command:
            result = await self.execute_command(command)
            await self.send_reply(message.sender, result)
        else:
            # Default: treat as inbox capture
            self.capture_to_inbox(message.text)
            await self.send_reply(message.sender, "✓ Captured to inbox")

    def parse_command(self, text: str) -> Optional[Command]:
        """
        Parse Datacore commands from message.

        Examples:
        - "today" → /today
        - "inbox: call John" → capture to inbox
        - "who is Ahmed" → CRM lookup
        - "search ZK proofs" → Datacortex search
        """

    async def execute_command(self, command: Command) -> str:
        """Execute command and return result summary."""

    async def send_message(self, to: str, text: str):
        """Send WhatsApp message via WAHA."""
```

### 6. Notification Service

Proactive notifications via WhatsApp.

**File:** `lib/whatsapp_notifications.py`

```python
class WhatsAppNotifications:
    """Push notifications to WhatsApp."""

    def __init__(self, gateway: WhatsAppGateway, owner_number: str):
        self.gateway = gateway
        self.owner = owner_number

    async def send_morning_briefing(self, briefing: str):
        """Send /today summary to WhatsApp."""

    async def send_follow_up_reminder(self, contact: str, context: str):
        """Remind about dormant contacts."""

    async def send_task_completed(self, task: str, result: str):
        """Notify when nightshift task completes."""
```

## Module Structure

```
.datacore/modules/whatsapp/
├── module.yaml
├── CLAUDE.base.md
├── README.md
├── lib/
│   ├── __init__.py
│   ├── whatsapp_export_parser.py
│   ├── whatsapp_adapter.py
│   ├── whatsapp_contact_creator.py
│   ├── whatsapp_gateway.py
│   ├── whatsapp_notifications.py
│   └── waha_client.py
├── commands/
│   ├── whatsapp.md              # /whatsapp command
│   └── whatsapp-gateway.md      # Gateway management
├── agents/
│   ├── whatsapp-import.md       # Import from exports
│   └── whatsapp-sync.md         # Sync via WAHA
└── templates/
    └── docker-compose.yaml      # WAHA deployment
```

## Configuration

### module.yaml

```yaml
name: whatsapp
version: 0.1.0
description: |
  WhatsApp integration for Datacore.
  Import contacts, track interactions, bidirectional messaging.

provides:
  commands:
    - whatsapp
  agents:
    - whatsapp-import
    - whatsapp-sync
  crm_adapters:
    - whatsapp

settings:
  waha_url:
    description: "WAHA gateway URL"
    default: "http://localhost:3000"

  allowed_numbers:
    description: "Phone numbers allowed to send commands"
    default: []

  auto_capture:
    description: "Capture unrecognized messages to inbox"
    default: true

  morning_briefing:
    description: "Send morning briefing via WhatsApp"
    default: false
    time: "07:00"

  export_directory:
    description: "Directory for WhatsApp exports"
    default: ".datacore/state/whatsapp/exports"

hooks:
  today: "commands/today-hook.md"        # Optional morning push
  nightshift_complete: "commands/notify-hook.md"
```

### State Directory

```
.datacore/state/whatsapp/
├── exports/                    # Drop .txt exports here
│   ├── *.txt
│   └── processed/              # Moved after import
├── sessions/                   # WAHA session data
├── phone-index.yaml            # Phone → contact mapping
└── gateway.log                 # Message log
```

## Command Interface

### /whatsapp

```markdown
# /whatsapp

## Menu

1. **Import exports** - Process .txt chat exports
2. **Sync contacts** - Sync from WAHA gateway
3. **Start gateway** - Start message listener
4. **Stop gateway** - Stop message listener
5. **Send message** - Send to contact
6. **Status** - Show gateway status
```

### Example Interactions

**Via Terminal:**
```bash
# Import exports
/whatsapp import

# Start gateway
/whatsapp gateway start

# Send message
/whatsapp send "Ahmed Bin Sulayem" "Following up on our Davos conversation..."
```

**Via WhatsApp (to yourself):**
```
You: today
Bot: 📅 Today's Briefing...

You: who is Ahmed Bin Sulayem
Bot: Ahmed Bin Sulayem | DMCC
     Executive Chairman & CEO
     Last contact: Davos 2025

You: remind me to follow up with Brett Krause
Bot: ✓ Captured to inbox
```

## Security Model

### Access Control

1. **Allowlist only** - Only configured phone numbers can send commands
2. **No external access** - WAHA runs on localhost only
3. **No sensitive commands** - Read-only by default, write requires confirmation

### Data Privacy

1. **All data stays local** - No cloud, no third parties
2. **Session data encrypted** - WAHA stores encrypted session
3. **Logs rotated** - Gateway logs auto-purge after 7 days

### Risk Mitigation

| Risk | Mitigation |
|------|------------|
| WhatsApp ban | Use official Business API for production |
| Prompt injection | No email/external content processing |
| Unauthorized access | Phone number allowlist |
| Data leak | Local-only deployment |

## Implementation Phases

### Phase 1: CRM Import (Week 1)
- [ ] WhatsApp export parser
- [ ] WhatsApp CRM adapter
- [ ] Contact creator from exports
- [ ] /whatsapp import command

### Phase 2: WAHA Gateway (Week 2)
- [ ] WAHA Docker setup
- [ ] WAHA Python client
- [ ] QR code pairing flow
- [ ] Basic send/receive

### Phase 3: Command Handler (Week 3)
- [ ] Message parsing
- [ ] Command routing
- [ ] Inbox capture
- [ ] CRM lookup
- [ ] /today summary

### Phase 4: Notifications (Week 4)
- [ ] Morning briefing push
- [ ] Follow-up reminders
- [ ] Nightshift completion alerts

## Alternatives Considered

### Baileys (Node.js)
- Pro: Most mature
- Con: Requires Node.js, harder to integrate with Python Datacore

### Official WhatsApp Business API
- Pro: No ban risk, official
- Con: Requires Meta approval, business account

### Moltbot
- Pro: Already built
- Con: Security risks, knowledge fragmentation (see analysis)

**Decision:** WAHA provides best balance - Python-friendly, self-hosted, simple.

## Related DIPs

- **DIP-0010**: External Sync Architecture - adapter pattern
- **DIP-0012**: CRM Module - integration point
- **DIP-0011**: Nightshift - notification hooks

## Open Questions

1. Should gateway run as daemon or on-demand?
2. Message history retention policy?
3. Group chat handling (ignore vs. special command prefix)?
4. Voice message transcription?

## References

- [WAHA Documentation](https://waha.devlike.pro/)
- [WhatsApp Business API](https://developers.facebook.com/docs/whatsapp)
- [Baileys](https://github.com/WhiskeySockets/Baileys)
- [DIP-0012 CRM Module](DIP-0012-crm-module.md)
