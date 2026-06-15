export class CircuitOpenError extends Error {
  constructor(message = "Circuit breaker is OPEN") {
    super(message);
    this.name = "CircuitOpenError";
  }
}

export class CircuitBreaker {
  private failures = 0;
  private lastFailureTime: number | null = null;
  state: "closed" | "open" | "half_open" = "closed";

  constructor(
    private failureThreshold = 5,
    private timeoutSec = 60,
  ) {}

  async call<T>(fn: () => Promise<T>): Promise<T> {
    if (this.state === "open") {
      if (this.lastFailureTime && Date.now() / 1000 - this.lastFailureTime > this.timeoutSec) {
        this.state = "half_open";
      } else {
        throw new CircuitOpenError();
      }
    }
    try {
      const result = await fn();
      if (this.state === "half_open") {
        this.state = "closed";
        this.failures = 0;
      }
      return result;
    } catch (err) {
      this.failures += 1;
      this.lastFailureTime = Date.now() / 1000;
      if (this.failures >= this.failureThreshold) this.state = "open";
      throw err;
    }
  }

  get status() {
    return {
      state: this.state,
      failures: this.failures,
      last_failure: this.lastFailureTime,
    };
  }
}

export class RateLimiter {
  private tokens: number;
  private lastRefill: number;

  constructor(
    private maxTokens: number,
    private refillPerSec: number,
  ) {
    this.tokens = maxTokens;
    this.lastRefill = Date.now();
  }

  tryAcquire(cost = 1): boolean {
    const now = Date.now();
    const elapsed = (now - this.lastRefill) / 1000;
    this.tokens = Math.min(this.maxTokens, this.tokens + elapsed * this.refillPerSec);
    this.lastRefill = now;
    if (this.tokens < cost) return false;
    this.tokens -= cost;
    return true;
  }
}

export const binanceCircuit = new CircuitBreaker(5, 60);
export const telegramCircuit = new CircuitBreaker(3, 30);

export async function withRetry<T>(
  fn: () => Promise<T>,
  attempts = 3,
  delayMs = 500,
): Promise<T> {
  let lastErr: unknown;
  for (let i = 0; i < attempts; i++) {
    try {
      return await fn();
    } catch (err) {
      lastErr = err;
      if (i < attempts - 1) await new Promise((r) => setTimeout(r, delayMs * (i + 1)));
    }
  }
  throw lastErr;
}
