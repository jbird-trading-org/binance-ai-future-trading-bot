import { loadEnv } from "../src/lib/env.js";
import { binanceGet } from "../src/lib/binance.js";

loadEnv();

async function main(): Promise<void> {
  const account = await binanceGet<{
    totalMarginBalance?: string;
    availableBalance?: string;
  }>("/fapi/v3/account", "", true);

  if (!account?.totalMarginBalance) {
    console.error("Failed to fetch account. Set BINANCE_API_KEY and BINANCE_SECRET in .env");
    process.exit(1);
  }

  const balance = Number.parseFloat(account.totalMarginBalance);
  const available = Number.parseFloat(account.availableBalance ?? "0");
  console.log(`💰 Balance: $${balance.toFixed(2)}`);
  console.log(`💵 Available: $${available.toFixed(2)}`);
  console.log(`⚠️ Margin Used: $${(balance - available).toFixed(2)}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
