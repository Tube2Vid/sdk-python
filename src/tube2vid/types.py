"""Response and request shapes of the public Tube2Vid API (/v1/*), mirroring openapi.yaml.

Responses are plain dicts typed with TypedDict, so keys match the JSON exactly (camelCase).
"""

from __future__ import annotations

from typing import Any, Literal, NotRequired, Optional, TypedDict

JobMode = Literal["auto", "video", "audio", "gallery"]
JobState = Literal["queued", "running", "completed", "failed"]
PlatformStatusValue = Literal["operational", "degraded", "partial_outage", "down", "beta"]
ApiKeyScope = Literal["jobs:write", "jobs:read", "usage:read", "keys:read", "keys:write", "billing:write"]


class ProofOfWork(TypedDict):
    nonce: str
    expiresAt: str
    difficulty: int
    signature: str
    solution: str


class JobSubmitInput(TypedDict):
    url: str
    platform: NotRequired[str]
    mode: NotRequired[JobMode]
    format: NotRequired[str]
    quality: NotRequired[str]
    turnstileToken: NotRequired[str]
    pow: NotRequired[ProofOfWork]


class QueuedJobResponse(TypedDict):
    jobId: str
    status: JobState
    platform: str
    estimatedCredits: int
    deduped: NotRequired[bool]


class PlatformProvider(TypedDict):
    id: str
    kind: str
    priority: int


class PlatformSummary(TypedDict):
    slug: str
    name: str
    category: str
    supportLevel: str
    publicClaim: bool
    capabilities: list[str]
    providers: list[PlatformProvider]


class PlatformHealthRow(TypedDict):
    platform: str
    name: str
    category: str
    supportLevel: str
    status: PlatformStatusValue
    auditCategory: str
    provider: NotRequired[str]
    providerKind: NotRequired[str]
    successRate: NotRequired[float]
    medianExtractMs: NotRequired[float]
    lastCheckedAt: NotRequired[str]
    note: NotRequired[str]
    reason: NotRequired[str]
    authNeeded: NotRequired[bool]
    repaired: NotRequired[bool]


class RecentDownload(TypedDict):
    platform: str
    title: NotRequired[str]
    sourceUrl: NotRequired[str]
    mode: str
    format: str
    status: str
    thumbnailUrl: NotRequired[str]
    createdAt: str


class JobEvent(TypedDict):
    id: str
    jobId: str
    stage: str
    message: str
    details: NotRequired[Optional[dict[str, Any]]]
    createdAt: str


class LatestEvent(TypedDict):
    stage: str
    message: NotRequired[str]
    details: NotRequired[Optional[dict[str, Any]]]
    createdAt: str


class PublicJobStatus(TypedDict):
    jobId: str
    platform: str
    status: JobState
    progress: float
    provider: NotRequired[str]
    fallback: NotRequired[bool]
    title: NotRequired[str]
    errorCode: NotRequired[str]
    errorMessage: NotRequired[str]
    completedAt: NotRequired[str]
    createdAt: str
    updatedAt: str
    latestEvent: NotRequired[LatestEvent]


class JobStatus(TypedDict):
    id: str
    jobId: NotRequired[str]
    userId: NotRequired[str]
    apiKeyId: NotRequired[str]
    url: str
    platform: str
    mode: JobMode
    format: str
    quality: str
    creditsReserved: int
    status: JobState
    progress: float
    creditsCharged: int
    provider: NotRequired[str]
    title: NotRequired[str]
    outputPath: NotRequired[str]
    outputStorageKey: NotRequired[str]
    outputSize: NotRequired[int]
    thumbnailUrl: NotRequired[str]
    errorCode: NotRequired[str]
    errorMessage: NotRequired[str]
    completedAt: NotRequired[str]
    createdAt: str
    updatedAt: str


class UsageSummary(TypedDict):
    creditBalance: int
    jobsTotal: int
    jobsCompleted: int
    jobsFailed: int


class StatusHistoryItem(TypedDict):
    id: str
    platform: str
    provider: str
    status: str
    durationMs: NotRequired[float]
    errorCode: NotRequired[str]
    errorMessage: NotRequired[str]
    createdAt: str


class ProviderFailureRate(TypedDict):
    provider: str
    total: int
    failed: int
    failureRate: float


class OpsAlert(TypedDict):
    level: Literal["info", "warn", "critical"]
    code: str
    message: str


class OperationalMetrics(TypedDict):
    generatedAt: str
    queueDepth: int
    queuedJobs: int
    runningJobs: int
    completedJobs24h: int
    failedJobs24h: int
    p95JobDurationMs: NotRequired[float]
    providerFailureRates: list[ProviderFailureRate]
    alerts: list[OpsAlert]


class ServiceHealth(TypedDict):
    ok: bool
    service: str
    time: str


class PowChallenge(TypedDict):
    nonce: str
    expiresAt: str
    difficulty: int
    signature: str


class ApiKeyCreateInput(TypedDict):
    name: str
    scopes: NotRequired[list[ApiKeyScope]]
    rateLimitPerMinute: NotRequired[int]


class CreatedApiKey(TypedDict):
    id: str
    name: str
    key: str
    prefix: str
    scopes: list[str]


class ApiKeySummary(TypedDict):
    id: str
    name: str
    prefix: str
    scopes: list[str]
    rateLimitPerMinute: int
    revokedAt: NotRequired[str]
    createdAt: str


class CheckoutInput(TypedDict, total=False):
    credits: int
    pack: Literal["starter", "builder", "scale"]


class CheckoutSession(TypedDict):
    checkoutUrl: Optional[str]
    mode: Literal["stripe", "placeholder"]
    sessionId: NotRequired[str]
    credits: int
    amountCents: int
    message: NotRequired[str]
