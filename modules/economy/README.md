# Economy module

Planned commands: `/economy`, `/balance`, `/daily`, `/work`, `/deposit`, `/withdraw`, `/transfer`, `/leaderboard`, `/market`, `/inventory`, `/addbalance`, `/resetbalance`, `/buy`, `/sell`, `/credit`, `/loan`, `/additem`.

MOP Points and inventory are **global across servers**. Marketplace product IDs and normalized names are globally unique. Stock changes and transfers require atomic database transactions; CSV is for export, not live inventory. No real-money, gambling, or crypto features. Not loaded until implemented.
