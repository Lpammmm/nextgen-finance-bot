import os
import discord
from discord import app_commands
import yfinance as yf
import feedparser
from urllib.parse import quote

TOKEN = os.environ["DISCORD_TOKEN"]  # defini dans Railway, jamais en clair

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


@client.event
async def on_ready():
    await tree.sync()
    print(f"Connecte en tant que {client.user}")


# ------- COMMANDE /action -------
@tree.command(name="action", description="Cours d'une action + variation + dernieres actus")
@app_commands.describe(ticker="Symbole boursier (ex: AIR.PA pour Airbus, AAPL pour Apple)")
async def action(interaction: discord.Interaction, ticker: str):
    await interaction.response.defer()
    ticker = ticker.strip().upper()

    try:
        t = yf.Ticker(ticker)
        info = t.fast_info
        prix = info.last_price
        veille = info.previous_close
        if prix is None or veille is None:
            raise ValueError("donnees indisponibles")

        variation = prix - veille
        pct = (variation / veille) * 100
        sens = "En hausse" if variation >= 0 else "En baisse"
        couleur = 0x2ecc71 if variation >= 0 else 0xe74c3c
        devise = getattr(info, "currency", "") or ""

        try:
            nom = t.info.get("shortName", ticker)
        except Exception:
            nom = ticker

        embed = discord.Embed(
            title=f"{nom} ({ticker})",
            description=(
                f"**{prix:.2f} {devise}**  -  {sens}\n"
                f"Variation du jour : **{variation:+.2f} {devise} ({pct:+.2f} %)**"
            ),
            color=couleur,
        )

        flux = feedparser.parse(
            f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={quote(ticker)}&region=FR&lang=fr-FR"
        )
        if flux.entries:
            lignes = [f"- [{e.title}]({e.link})" for e in flux.entries[:5]]
            embed.add_field(
                name="Dernieres actus (pour comprendre le mouvement)",
                value="\n".join(lignes),
                inline=False,
            )
        else:
            embed.add_field(
                name="Actus",
                value="Aucune actu recente trouvee pour ce titre.",
                inline=False,
            )

        embed.set_footer(text="Donnees Yahoo Finance | Contenu informatif, pas un conseil en investissement.")
        await interaction.followup.send(embed=embed)

    except Exception:
        await interaction.followup.send(
            f"Impossible de trouver le titre `{ticker}`.\n"
            f"Verifie le symbole. Exemples : `AIR.PA` (Airbus), `MC.PA` (LVMH), "
            f"`AAPL` (Apple), `BTC-EUR` (Bitcoin)."
        )


# ------- COMMANDE /simulateur-pea -------
@tree.command(name="simulateur-pea", description="Simule la croissance d'un PEA (interets composes + fiscalite)")
@app_commands.describe(
    versement_initial="Montant de depart en euros",
    versement_mensuel="Versement chaque mois en euros",
    duree_annees="Nombre d'annees",
    rendement_annuel="Rendement annuel espere en % (ex: 7)",
)
async def simulateur_pea(
    interaction: discord.Interaction,
    versement_initial: float,
    versement_mensuel: float,
    duree_annees: int,
    rendement_annuel: float,
):
    taux_mensuel = (rendement_annuel / 100) / 12
    mois = duree_annees * 12

    capital = versement_initial
    total_verse = versement_initial
    for _ in range(mois):
        capital = capital * (1 + taux_mensuel) + versement_mensuel
        total_verse += versement_mensuel

    gains = capital - total_verse

    if duree_annees >= 5:
        impot = gains * 0.172
        note_fisca = "PEA de plus de 5 ans : gains exoneres d'impot sur le revenu, seuls les prelevements sociaux (17,2 %) s'appliquent."
    else:
        impot = gains * 0.30
        note_fisca = "PEA de moins de 5 ans : un retrait entraine la cloture et une taxation des gains a la flat tax (30 %)."

    net = capital - impot

    embed = discord.Embed(
        title="Simulateur de PEA",
        color=0x2b6cb0,
        description=(
            f"**Hypotheses**\n"
            f"- Versement initial : {versement_initial:,.0f} euros\n"
            f"- Versement mensuel : {versement_mensuel:,.0f} euros\n"
            f"- Duree : {duree_annees} ans\n"
            f"- Rendement annuel : {rendement_annuel:.1f} %\n"
        ),
    )
    embed.add_field(name="Total verse", value=f"{total_verse:,.0f} euros", inline=True)
    embed.add_field(name="Capital final (brut)", value=f"{capital:,.0f} euros", inline=True)
    embed.add_field(name="Plus-value", value=f"{gains:,.0f} euros", inline=True)
    embed.add_field(name="Fiscalite estimee", value=f"-{impot:,.0f} euros", inline=True)
    embed.add_field(name="Capital net estime", value=f"**{net:,.0f} euros**", inline=True)
    embed.add_field(name="Note fiscale", value=note_fisca, inline=False)
    embed.set_footer(text="Estimation simplifiee | Verifie les regles a jour sur service-public.fr | Pas un conseil en investissement.")

    await interaction.response.send_message(embed=embed)


client.run(TOKEN)
