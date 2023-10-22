def calculate_elo(stats, old_elo=1000):
    weight = max(2 - 0.1 * ((old_elo - 800) / 100), 0.1)
    return round((stats["kills"] + 
            stats["assists"] * 0.5 +
            stats["2ks"] * 2 + 
            stats["3ks"] * 3 + 
            stats["4ks"] * 4 +
            stats["5ks"] * 5 +
            stats["win"] * 5) * weight - \
            stats["deaths"])


# Example usage:
stats = {
    "kills": 20,
    "assists": 5,
    "deaths": 5,
    "mvps": 3,
    "score": 3000,
    "2ks": 2,
    "3ks": 1,
    "4ks": 0,
    "5ks": 0,
    "kills_with_headshot": 15,
    "kills_with_pistol": 5,
    "kills_with_sniper": 2,
    "damage_dealt": 1500,
    "win": 1
}
old_elo = 1000

new_elo = calculate_elo(stats, old_elo)
print(f"New Elo: {new_elo}")
