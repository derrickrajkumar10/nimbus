import type {
  Event,
  Hazard,
  Proposal,
  ProposalStatus,
  RankedSos,
  Reading,
  Resource1 as Resource,
  Segment,
  SegmentRisk,
  Sos,
  WardAlertDraft,
  WorkOrder,
} from '@contracts/generated/ts/nimbus'

/** An SOS, plus Triage's ranking once it has one (`GET /sos`). */
export type SosRow = Sos & Partial<Omit<RankedSos, 'sos_id'>>

export type Decision = 'approved' | 'edited' | 'rejected'
export type DecisionInput = { decision: Decision; decided_by: string; action?: WorkOrder | WardAlertDraft }

export type DecisionErrorCode = 'already_decided' | 'proposal_not_found' | 'event_not_sent' | 'invalid' | 'network'
export type DecisionErrorDetail = { current_status?: ProposalStatus; decided_by?: string | null }

export class DecisionError extends Error {
  readonly code: DecisionErrorCode
  readonly detail: DecisionErrorDetail

  constructor(code: DecisionErrorCode, message: string, detail: DecisionErrorDetail = {}) {
    super(message)
    this.name = 'DecisionError'
    this.code = code
    this.detail = detail
  }
}

export type ActivityPage = { items: Event[]; cursor: string | null }

/** One hour of rain at a Run's location. `time` is ISO with +05:30. */
export type RainPoint = { time: string; mm: number }

export type ReplaySpeed = 15 | 30 | 60 | 120
export type ReplayState = { playing: boolean; speed: ReplaySpeed }

export interface ReplayControl {
  get(runId: string): ReplayState
  set(runId: string, next: ReplayState): Promise<ReplayState>
}

export interface CommanderClient {
  ask(question: string, runId: string): AsyncIterable<string>
}

export interface NimbusSource {
  readonly mode: 'fixtures' | 'http'
  runs(): string[]
  segments(): Promise<Segment[]>
  risk(runId: string): Promise<SegmentRisk[]>
  readings(runId: string): Promise<Reading[]>
  hazards(runId: string): Promise<Hazard[]>
  resources(runId: string): Promise<Resource[]>
  sos(runId: string): Promise<SosRow[]>
  /** Every Proposal in the Run, whatever its status. */
  proposals(runId: string): Promise<Proposal[]>
  /** Oldest first. `since` is the exclusive cursor from the previous page. */
  activity(runId: string, since?: string | null): Promise<ActivityPage>
  decide(runId: string, proposalId: string, input: DecisionInput): Promise<Proposal>
  rain(runId: string): Promise<RainPoint[]>
  readonly replay: ReplayControl
  commander: CommanderClient
}
