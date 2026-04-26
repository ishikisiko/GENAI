const CASE_ID = "00000000-0000-0000-0000-000000000001";
const GLOBAL_DOC_NEWS_ID = "10000000-0000-0000-0000-000000000011";
const GLOBAL_DOC_COMPLAINT_ID = "10000000-0000-0000-0000-000000000012";
const GLOBAL_DOC_STATEMENT_ID = "10000000-0000-0000-0000-000000000013";
const GLOBAL_DOC_DUPLICATE_ID = "10000000-0000-0000-0000-000000000014";
const TOPIC_FOOD_SAFETY_ID = "20000000-0000-0000-0000-000000000001";
const TOPIC_SALMONELLA_ID = "20000000-0000-0000-0000-000000000002";
const TOPIC_REGULATORY_ID = "20000000-0000-0000-0000-000000000003";
const ASSIGN_NEWS_ID = "21000000-0000-0000-0000-000000000011";
const ASSIGN_COMPLAINT_ID = "21000000-0000-0000-0000-000000000012";
const ASSIGN_STATEMENT_ID = "21000000-0000-0000-0000-000000000013";
const DOC_NEWS_ID = "00000000-0000-0000-0000-000000000011";
const DOC_COMPLAINT_ID = "00000000-0000-0000-0000-000000000012";
const DOC_STATEMENT_ID = "00000000-0000-0000-0000-000000000013";

const ENT_NUTRIPLUS = "00000000-0000-0000-0000-000000000021";
const ENT_FDA = "00000000-0000-0000-0000-000000000022";
const ENT_CONSUMERS = "00000000-0000-0000-0000-000000000023";
const ENT_DISTRIBUTOR = "00000000-0000-0000-0000-000000000024";
const ENT_CEO = "00000000-0000-0000-0000-000000000025";
const ENT_HOSPITAL = "00000000-0000-0000-0000-000000000026";
const ENT_PRODUCT = "00000000-0000-0000-0000-000000000027";
const ENT_LAB = "00000000-0000-0000-0000-000000000028";

const RUN_BASELINE_ID = "00000000-0000-0000-0000-000000000031";
const RUN_APOLOGY_ID = "00000000-0000-0000-0000-000000000032";
const RUN_CLARIFICATION_ID = "00000000-0000-0000-0000-000000000033";

const AGENT_CONSUMER_ID = "00000000-0000-0000-0000-000000000041";
const AGENT_SUPPORTER_ID = "00000000-0000-0000-0000-000000000042";
const AGENT_CRITIC_ID = "00000000-0000-0000-0000-000000000043";
const AGENT_MEDIA_ID = "00000000-0000-0000-0000-000000000044";

export const DEMO_CASE_TITLE = "NutriPlus Protein Bar Salmonella Contamination (2024)";
export { CASE_ID as DEMO_CASE_ID };

export const demoCase = {
  id: CASE_ID,
  title: DEMO_CASE_TITLE,
  description:
    "A major food safety crisis involving NutriPlus Inc., a protein bar manufacturer. Lab tests confirmed Salmonella contamination in the ProMax series, leading to 47 reported hospitalizations across 12 states. The FDA initiated a mandatory recall. This demo shows how three different response strategies diverge over five simulation rounds.",
  status: "simulated",
};

export const demoGlobalDocs = [
  {
    id: GLOBAL_DOC_NEWS_ID,
    title: "Breaking: NutriPlus Protein Bars Linked to Salmonella Outbreak",
    canonical_url: "https://demo.sources/nutriplus/salmonella-outbreak",
    content_hash: "demo-salmonella-outbreak-news",
    source_kind: "news",
    authority_level: "medium",
    freshness_status: "current",
    source_status: "active",
    source_metadata: { provider: "demo", usage_note: "Seeded news context" },
    content:
      "Health officials confirmed today that NutriPlus ProMax protein bars are linked to a Salmonella outbreak affecting 47 people across 12 states. The FDA issued a mandatory recall of all ProMax SKUs with best-by dates between March and September 2024. Three patients remain hospitalized in critical condition. NutriPlus has not yet issued a public statement. The recall covers approximately 2.3 million units distributed through major retailers including Walmart, Target, and Amazon.",
    doc_type: "news",
  },
  {
    id: GLOBAL_DOC_COMPLAINT_ID,
    title: "Consumer Complaint Batch — ProMax Salmonella Symptoms",
    canonical_url: null,
    content_hash: "demo-promax-complaints",
    source_kind: "complaint",
    authority_level: "medium",
    freshness_status: "current",
    source_status: "active",
    source_metadata: { provider: "demo", usage_note: "Aggregated complaint signal" },
    content:
      "Aggregated consumer complaints (n=312): Symptoms reported include severe nausea, vomiting, diarrhea, and fever within 12–72 hours of consuming NutriPlus ProMax bars. Multiple complainants note NutriPlus customer service was unreachable for 48+ hours after the story broke. Several complainants report medical bills exceeding $3,000 and request reimbursement. A class action lawsuit is being organized by attorney groups in California and Texas. Consumer trust scores on product review platforms have dropped from 4.2/5 to 1.1/5 within 48 hours.",
    doc_type: "complaint",
  },
  {
    id: GLOBAL_DOC_STATEMENT_ID,
    title: "NutriPlus Official Statement — Initial Response",
    canonical_url: "https://demo.sources/nutriplus/official-initial-response",
    content_hash: "demo-nutriplus-official-response",
    source_kind: "official",
    authority_level: "high",
    freshness_status: "current",
    source_status: "active",
    source_metadata: { provider: "demo", usage_note: "Official company response" },
    content:
      "NutriPlus Inc. is aware of the FDA's inquiry regarding our ProMax protein bar product line. We take food safety extremely seriously and are cooperating fully with regulatory authorities. As a precautionary measure, we have voluntarily initiated a recall of ProMax products manufactured between January–August 2024. We are conducting a thorough internal investigation with third-party laboratory partners. Consumer health and safety is our highest priority. We will provide updates as the investigation progresses. Affected consumers may contact our dedicated recall hotline.",
    doc_type: "statement",
  },
  {
    id: GLOBAL_DOC_DUPLICATE_ID,
    title: "Wire Copy: NutriPlus Salmonella Outbreak",
    canonical_url: "https://demo.sources/wire/nutriplus-salmonella-copy",
    content_hash: "demo-salmonella-outbreak-news",
    source_kind: "news",
    authority_level: "low",
    freshness_status: "current",
    source_status: "active",
    source_metadata: { provider: "demo", usage_note: "Intentional duplicate candidate" },
    content:
      "Health officials confirmed today that NutriPlus ProMax protein bars are linked to a Salmonella outbreak affecting 47 people across 12 states. The FDA issued a mandatory recall of all ProMax SKUs with best-by dates between March and September 2024.",
    doc_type: "news",
  },
];

export const demoSourceTopics = [
  {
    id: TOPIC_FOOD_SAFETY_ID,
    name: "Food Safety Crises",
    description: "Reusable food contamination and public health source material.",
    parent_topic_id: null,
    topic_type: "crisis",
    status: "active",
  },
  {
    id: TOPIC_SALMONELLA_ID,
    name: "NutriPlus Salmonella Outbreak",
    description: "Sources directly relevant to the NutriPlus ProMax Salmonella crisis.",
    parent_topic_id: TOPIC_FOOD_SAFETY_ID,
    topic_type: "crisis",
    status: "active",
  },
  {
    id: TOPIC_REGULATORY_ID,
    name: "Regulatory Response",
    description: "Official statements, regulator updates, and recall process sources.",
    parent_topic_id: TOPIC_FOOD_SAFETY_ID,
    topic_type: "stakeholder",
    status: "active",
  },
];

export const demoCaseSourceTopics = [
  {
    id: "22000000-0000-0000-0000-000000000001",
    case_id: CASE_ID,
    topic_id: TOPIC_SALMONELLA_ID,
    relation_type: "primary",
    reason: "Demo crisis topic seeded from the case narrative.",
  },
  {
    id: "22000000-0000-0000-0000-000000000002",
    case_id: CASE_ID,
    topic_id: TOPIC_REGULATORY_ID,
    relation_type: "related",
    reason: "Regulatory sources are central to recall grounding.",
  },
];

export const demoSourceTopicAssignments = [
  {
    id: ASSIGN_NEWS_ID,
    global_source_id: GLOBAL_DOC_NEWS_ID,
    topic_id: TOPIC_SALMONELLA_ID,
    relevance_score: 0.95,
    reason: "Primary news account for the outbreak timeline.",
    assigned_by: "seed",
    status: "active",
    assignment_metadata: { demo: true },
  },
  {
    id: ASSIGN_COMPLAINT_ID,
    global_source_id: GLOBAL_DOC_COMPLAINT_ID,
    topic_id: TOPIC_SALMONELLA_ID,
    relevance_score: 0.86,
    reason: "Consumer impact and lawsuit signal for the crisis topic.",
    assigned_by: "seed",
    status: "active",
    assignment_metadata: { demo: true },
  },
  {
    id: ASSIGN_STATEMENT_ID,
    global_source_id: GLOBAL_DOC_STATEMENT_ID,
    topic_id: TOPIC_REGULATORY_ID,
    relevance_score: 0.78,
    reason: "Official company response linked to the regulatory response topic.",
    assigned_by: "seed",
    status: "active",
    assignment_metadata: { demo: true },
  },
];

export const demoDocs = [
  {
    id: DOC_NEWS_ID,
    case_id: CASE_ID,
    global_source_id: GLOBAL_DOC_NEWS_ID,
    source_topic_id: TOPIC_SALMONELLA_ID,
    source_topic_assignment_id: ASSIGN_NEWS_ID,
    source_origin: "case_upload",
    title: "Breaking: NutriPlus Protein Bars Linked to Salmonella Outbreak",
    content:
      "Health officials confirmed today that NutriPlus ProMax protein bars are linked to a Salmonella outbreak affecting 47 people across 12 states. The FDA issued a mandatory recall of all ProMax SKUs with best-by dates between March and September 2024. Three patients remain hospitalized in critical condition. NutriPlus has not yet issued a public statement. The recall covers approximately 2.3 million units distributed through major retailers including Walmart, Target, and Amazon.",
    doc_type: "news",
    source_metadata: { selected_topic_id: TOPIC_SALMONELLA_ID, selected_assignment_id: ASSIGN_NEWS_ID },
  },
  {
    id: DOC_COMPLAINT_ID,
    case_id: CASE_ID,
    global_source_id: GLOBAL_DOC_COMPLAINT_ID,
    source_topic_id: TOPIC_SALMONELLA_ID,
    source_topic_assignment_id: ASSIGN_COMPLAINT_ID,
    source_origin: "case_upload",
    title: "Consumer Complaint Batch — ProMax Salmonella Symptoms",
    content:
      "Aggregated consumer complaints (n=312): Symptoms reported include severe nausea, vomiting, diarrhea, and fever within 12–72 hours of consuming NutriPlus ProMax bars. Multiple complainants note NutriPlus customer service was unreachable for 48+ hours after the story broke. Several complainants report medical bills exceeding $3,000 and request reimbursement. A class action lawsuit is being organized by attorney groups in California and Texas. Consumer trust scores on product review platforms have dropped from 4.2/5 to 1.1/5 within 48 hours.",
    doc_type: "complaint",
    source_metadata: { selected_topic_id: TOPIC_SALMONELLA_ID, selected_assignment_id: ASSIGN_COMPLAINT_ID },
  },
  {
    id: DOC_STATEMENT_ID,
    case_id: CASE_ID,
    global_source_id: GLOBAL_DOC_STATEMENT_ID,
    source_topic_id: TOPIC_REGULATORY_ID,
    source_topic_assignment_id: ASSIGN_STATEMENT_ID,
    source_origin: "case_upload",
    title: "NutriPlus Official Statement — Initial Response",
    content:
      "NutriPlus Inc. is aware of the FDA's inquiry regarding our ProMax protein bar product line. We take food safety extremely seriously and are cooperating fully with regulatory authorities. As a precautionary measure, we have voluntarily initiated a recall of ProMax products manufactured between January–August 2024. We are conducting a thorough internal investigation with third-party laboratory partners. Consumer health and safety is our highest priority. We will provide updates as the investigation progresses. Affected consumers may contact our dedicated recall hotline.",
    doc_type: "statement",
    source_metadata: { selected_topic_id: TOPIC_REGULATORY_ID, selected_assignment_id: ASSIGN_STATEMENT_ID },
  },
];

export const demoEntities = [
  { id: ENT_NUTRIPLUS, case_id: CASE_ID, name: "NutriPlus Inc.", entity_type: "organization", description: "Protein supplement manufacturer at the center of the contamination crisis. Founded 2011, annual revenue ~$340M." },
  { id: ENT_FDA, case_id: CASE_ID, name: "U.S. Food and Drug Administration (FDA)", entity_type: "organization", description: "Federal regulatory body that issued the mandatory recall order and is conducting the official investigation." },
  { id: ENT_CONSUMERS, case_id: CASE_ID, name: "Affected Consumers Group", entity_type: "person", description: "312+ consumers who reported illness; organizing class action lawsuit." },
  { id: ENT_DISTRIBUTOR, case_id: CASE_ID, name: "NutraChain Distributors", entity_type: "organization", description: "Third-party logistics and distribution partner responsible for cold-chain storage of the recalled products." },
  { id: ENT_CEO, case_id: CASE_ID, name: "Marcus Webb (CEO, NutriPlus)", entity_type: "person", description: "Chief Executive Officer of NutriPlus Inc. Absent from public communications for 72 hours after initial outbreak news broke." },
  { id: ENT_HOSPITAL, case_id: CASE_ID, name: "Regional Medical Centers", entity_type: "organization", description: "Hospitals in 12 states treating patients affected by the outbreak. Three patients in critical condition." },
  { id: ENT_PRODUCT, case_id: CASE_ID, name: "ProMax Protein Bars (Contaminated Batch)", entity_type: "product", description: "NutriPlus ProMax line, 2.3 million units recalled. Best-by dates March–September 2024. Salmonella Typhimurium detected." },
  { id: ENT_LAB, case_id: CASE_ID, name: "BioSafe Testing Laboratories", entity_type: "organization", description: "Third-party laboratory that confirmed Salmonella Typhimurium contamination in NutriPlus ProMax samples." },
];

export const demoRelations = [
  { case_id: CASE_ID, source_entity_id: ENT_NUTRIPLUS, target_entity_id: ENT_PRODUCT, relation_type: "manufactured", description: "NutriPlus manufactured the contaminated ProMax batch." },
  { case_id: CASE_ID, source_entity_id: ENT_FDA, target_entity_id: ENT_NUTRIPLUS, relation_type: "regulates", description: "FDA issued mandatory recall order and is investigating NutriPlus." },
  { case_id: CASE_ID, source_entity_id: ENT_LAB, target_entity_id: ENT_PRODUCT, relation_type: "tested", description: "BioSafe Labs confirmed Salmonella Typhimurium in ProMax samples." },
  { case_id: CASE_ID, source_entity_id: ENT_CONSUMERS, target_entity_id: ENT_PRODUCT, relation_type: "harmed_by", description: "312+ consumers reported illness after consuming recalled products." },
  { case_id: CASE_ID, source_entity_id: ENT_DISTRIBUTOR, target_entity_id: ENT_PRODUCT, relation_type: "distributed", description: "NutraChain Distributors responsible for cold-chain handling of recalled batch." },
  { case_id: CASE_ID, source_entity_id: ENT_CEO, target_entity_id: ENT_NUTRIPLUS, relation_type: "leads", description: "Marcus Webb is CEO and faces public pressure to appear and respond." },
];

export const demoClaims = [
  { case_id: CASE_ID, content: "NutriPlus ProMax bars caused 47 confirmed Salmonella hospitalizations across 12 states.", claim_type: "fact", credibility: "high", source_doc_id: DOC_NEWS_ID },
  { case_id: CASE_ID, content: "NutriPlus deliberately withheld internal lab results showing contamination risk for 3 weeks before the recall.", claim_type: "allegation", credibility: "low", source_doc_id: DOC_COMPLAINT_ID },
  { case_id: CASE_ID, content: "The FDA issued a mandatory recall of 2.3 million ProMax units manufactured January–August 2024.", claim_type: "fact", credibility: "high", source_doc_id: DOC_NEWS_ID },
  { case_id: CASE_ID, content: "NutriPlus customer service was completely unreachable for 48 hours after the crisis broke.", claim_type: "statement", credibility: "medium", source_doc_id: DOC_COMPLAINT_ID },
  { case_id: CASE_ID, content: "NutraChain Distributors may have broken cold-chain requirements, contributing to bacterial growth.", claim_type: "allegation", credibility: "low", source_doc_id: null },
  { case_id: CASE_ID, content: "NutriPlus is cooperating fully with the FDA and conducting third-party laboratory investigation.", claim_type: "statement", credibility: "medium", source_doc_id: DOC_STATEMENT_ID },
  { case_id: CASE_ID, content: "A class-action lawsuit is being organized by consumer groups in California and Texas.", claim_type: "event", credibility: "high", source_doc_id: DOC_COMPLAINT_ID },
  { case_id: CASE_ID, content: "CEO Marcus Webb was absent from all public communications for over 72 hours after the outbreak was confirmed.", claim_type: "fact", credibility: "high", source_doc_id: null },
];

export const demoAgents = [
  {
    id: AGENT_CONSUMER_ID,
    case_id: CASE_ID,
    role: "consumer",
    stance: "angry and demanding accountability",
    concern: "health safety, medical compensation, and product trust",
    emotional_sensitivity: 0.85,
    spread_tendency: 0.7,
    initial_beliefs: ["NutriPlus put profits over safety", "We deserve full compensation", "The recall came too late"],
    persona_description: "An affected parent whose child was hospitalized after consuming ProMax bars. Active on social media, member of the class-action group, and highly vocal about the lack of communication from NutriPlus.",
  },
  {
    id: AGENT_SUPPORTER_ID,
    case_id: CASE_ID,
    role: "supporter",
    stance: "cautiously supportive, willing to give benefit of the doubt",
    concern: "preserving a brand they trust if evidence shows good faith",
    emotional_sensitivity: 0.45,
    spread_tendency: 0.4,
    initial_beliefs: ["NutriPlus has been a good brand for years", "Contamination can happen to anyone", "Waiting to hear the full story"],
    persona_description: "A long-time NutriPlus customer and fitness enthusiast. Has used their products for 5 years without issue. Skeptical of the class-action group but concerned about the hospitalization reports.",
  },
  {
    id: AGENT_CRITIC_ID,
    case_id: CASE_ID,
    role: "critic",
    stance: "highly skeptical, demands systemic accountability",
    concern: "food safety regulation failures, corporate transparency",
    emotional_sensitivity: 0.65,
    spread_tendency: 0.8,
    initial_beliefs: ["FDA oversight is too weak", "NutriPlus will try to minimize liability", "The distribution partner is being scapegoated"],
    persona_description: "A food safety advocate and blogger with 80,000 followers. Has written critically about FDA enforcement gaps. Tracks corporate crisis responses and grades their transparency.",
  },
  {
    id: AGENT_MEDIA_ID,
    case_id: CASE_ID,
    role: "media",
    stance: "objective but aggressive in pursuing facts",
    concern: "timeline accuracy, corporate culpability, and regulatory response",
    emotional_sensitivity: 0.3,
    spread_tendency: 0.9,
    initial_beliefs: ["CEO silence is a major story angle", "Need to verify the cold-chain allegation", "Recall timing is key to liability"],
    persona_description: "An investigative reporter for a national health and consumer news outlet. Working on a full exposé. Has FOIA'd FDA correspondence with NutriPlus and is tracking down the lab results timeline.",
  },
];

export const demoRuns = [
  {
    id: RUN_BASELINE_ID,
    case_id: CASE_ID,
    run_type: "baseline",
    strategy_type: null,
    strategy_message: null,
    injection_round: null,
    total_rounds: 5,
    status: "completed",
    error_message: null,
    completed_at: new Date().toISOString(),
  },
  {
    id: RUN_APOLOGY_ID,
    case_id: CASE_ID,
    run_type: "intervention",
    strategy_type: "apology",
    strategy_message: "NutriPlus CEO Marcus Webb issues a full public apology, takes personal responsibility, announces a $5M consumer compensation fund, and commits to a third-party supply chain audit with results published publicly within 60 days.",
    injection_round: 2,
    total_rounds: 5,
    status: "completed",
    error_message: null,
    completed_at: new Date().toISOString(),
  },
  {
    id: RUN_CLARIFICATION_ID,
    case_id: CASE_ID,
    run_type: "intervention",
    strategy_type: "clarification",
    strategy_message: "NutriPlus publishes a detailed timeline showing when contamination was detected, what regulatory notifications were made, and evidence pointing to cold-chain mishandling by the distributor as the primary cause.",
    injection_round: 3,
    total_rounds: 5,
    status: "completed",
    error_message: null,
    completed_at: new Date().toISOString(),
  },
];

const baselineRounds = [
  {
    run_id: RUN_BASELINE_ID,
    round_number: 1,
    overall_sentiment: -0.31,
    polarization_level: 0.42,
    narrative_state: "Initial shock phase. News of the contamination spreads rapidly. NutriPlus's silence amplifies public anxiety. Social media fills with firsthand accounts from affected consumers.",
    strategy_applied: null,
    agent_responses: [
      { agent_id: AGENT_CONSUMER_ID, role: "consumer", response: "My daughter spent two nights in hospital because of their bars. The company won't even pick up the phone. I'm sharing this everywhere.", sentiment_delta: -0.45, amplification: 0.78 },
      { agent_id: AGENT_SUPPORTER_ID, role: "supporter", response: "This is really alarming. I've been buying NutriPlus for years. I need to hear from them directly before I draw any conclusions.", sentiment_delta: -0.12, amplification: 0.25 },
      { agent_id: AGENT_CRITIC_ID, role: "critic", response: "The FDA recall is mandatory — that's not voluntary. NutriPlus is already spinning this. Where are the internal lab dates?", sentiment_delta: -0.38, amplification: 0.72 },
      { agent_id: AGENT_MEDIA_ID, role: "media", response: "CEO Marcus Webb has not appeared publicly in 72 hours. We have confirmed 47 hospitalizations. The silence story is as big as the contamination story.", sentiment_delta: -0.25, amplification: 0.88 },
    ],
  },
  {
    run_id: RUN_BASELINE_ID,
    round_number: 2,
    overall_sentiment: -0.49,
    polarization_level: 0.56,
    narrative_state: "NutriPlus continues to issue only boilerplate corporate statements. The class-action lawsuit gains media traction. The distributor cold-chain allegation begins circulating on social platforms.",
    strategy_applied: null,
    agent_responses: [
      { agent_id: AGENT_CONSUMER_ID, role: "consumer", response: "The class action now has 400 members. Their PR statement is an insult. 'Highest priority' — yet zero compensation offered.", sentiment_delta: -0.52, amplification: 0.82 },
      { agent_id: AGENT_SUPPORTER_ID, role: "supporter", response: "I'm starting to worry. The cold-chain story is damning if true. Why isn't NutriPlus addressing it directly?", sentiment_delta: -0.28, amplification: 0.38 },
      { agent_id: AGENT_CRITIC_ID, role: "critic", response: "NutraChain being scapegoated is a classic deflection tactic. NutriPlus owns the quality control process regardless of who stored it.", sentiment_delta: -0.44, amplification: 0.79 },
      { agent_id: AGENT_MEDIA_ID, role: "media", response: "We've obtained shipping records. The cold-chain breach appears to have occurred before the product left NutriPlus's facility, not during distribution.", sentiment_delta: -0.35, amplification: 0.91 },
    ],
  },
  {
    run_id: RUN_BASELINE_ID,
    round_number: 3,
    overall_sentiment: -0.63,
    polarization_level: 0.67,
    narrative_state: "Investigative journalism confirms internal timeline discrepancies. Stock price drops 18%. Retailers begin voluntarily removing all NutriPlus products pending investigation. Polarization deepens.",
    strategy_applied: null,
    agent_responses: [
      { agent_id: AGENT_CONSUMER_ID, role: "consumer", response: "Walmart pulled all their products. Even the ones not recalled. This company is finished. I will never trust them again.", sentiment_delta: -0.61, amplification: 0.85 },
      { agent_id: AGENT_SUPPORTER_ID, role: "supporter", response: "Even I'm struggling to defend them now. The internal timeline the reporter exposed is very hard to explain away.", sentiment_delta: -0.43, amplification: 0.42 },
      { agent_id: AGENT_CRITIC_ID, role: "critic", response: "They knew. The FDA records show a notification three weeks before the recall. This isn't an accident — it's negligence.", sentiment_delta: -0.58, amplification: 0.84 },
      { agent_id: AGENT_MEDIA_ID, role: "media", response: "FOIA documents show FDA warned NutriPlus of elevated contamination risk on July 3. The recall wasn't announced until August 1.", sentiment_delta: -0.47, amplification: 0.93 },
    ],
  },
  {
    run_id: RUN_BASELINE_ID,
    round_number: 4,
    overall_sentiment: -0.74,
    polarization_level: 0.75,
    narrative_state: "Congressional hearing called. CEO finally speaks but response is perceived as defensive and scripted. Consumer anger reaches a peak. Brand NPS hits historic low.",
    strategy_applied: null,
    agent_responses: [
      { agent_id: AGENT_CONSUMER_ID, role: "consumer", response: "Webb's interview was pathetic. He blamed everyone but himself. We're going to make sure this company pays.", sentiment_delta: -0.72, amplification: 0.88 },
      { agent_id: AGENT_SUPPORTER_ID, role: "supporter", response: "I defended NutriPlus for weeks. After that interview I'm done. He had a chance to make it right and he blew it.", sentiment_delta: -0.65, amplification: 0.55 },
      { agent_id: AGENT_CRITIC_ID, role: "critic", response: "The CEO interview confirmed every suspicion. 'We followed proper protocols' is not an apology when people were hospitalized.", sentiment_delta: -0.7, amplification: 0.86 },
      { agent_id: AGENT_MEDIA_ID, role: "media", response: "The Webb interview is generating massive backlash. Congressional subcommittee has requested internal communications from NutriPlus going back 12 months.", sentiment_delta: -0.55, amplification: 0.94 },
    ],
  },
  {
    run_id: RUN_BASELINE_ID,
    round_number: 5,
    overall_sentiment: -0.79,
    polarization_level: 0.81,
    narrative_state: "Crisis fully entrenched. Brand damage severe and likely permanent. Regulatory action escalating. No strategic response — the silence and defensiveness have become the defining narrative.",
    strategy_applied: null,
    agent_responses: [
      { agent_id: AGENT_CONSUMER_ID, role: "consumer", response: "The class action is now federal. Over 800 plaintiffs. NutriPlus's market cap has dropped $200M. This is what silence costs.", sentiment_delta: -0.81, amplification: 0.89 },
      { agent_id: AGENT_SUPPORTER_ID, role: "supporter", response: "There is nothing left to support. The company failed every test — scientific, moral, and communicative.", sentiment_delta: -0.77, amplification: 0.6 },
      { agent_id: AGENT_CRITIC_ID, role: "critic", response: "This is a case study in how not to handle a food safety crisis. The regulatory consequences will be severe and deserved.", sentiment_delta: -0.79, amplification: 0.87 },
      { agent_id: AGENT_MEDIA_ID, role: "media", response: "NutriPlus's case has been referred to the DOJ. This has moved from a PR crisis to a potential criminal investigation.", sentiment_delta: -0.68, amplification: 0.95 },
    ],
  },
];

const apologyRounds = [
  {
    run_id: RUN_APOLOGY_ID,
    round_number: 1,
    overall_sentiment: -0.31,
    polarization_level: 0.42,
    narrative_state: "Initial shock phase identical to baseline. News of contamination spreads rapidly. NutriPlus has not yet responded strategically.",
    strategy_applied: null,
    agent_responses: [
      { agent_id: AGENT_CONSUMER_ID, role: "consumer", response: "My daughter spent two nights in hospital because of their bars. The company won't even pick up the phone. I'm sharing this everywhere.", sentiment_delta: -0.45, amplification: 0.78 },
      { agent_id: AGENT_SUPPORTER_ID, role: "supporter", response: "This is really alarming. I've been buying NutriPlus for years. I need to hear from them directly before I draw any conclusions.", sentiment_delta: -0.12, amplification: 0.25 },
      { agent_id: AGENT_CRITIC_ID, role: "critic", response: "The FDA recall is mandatory — that's not voluntary. NutriPlus is already spinning this. Where are the internal lab dates?", sentiment_delta: -0.38, amplification: 0.72 },
      { agent_id: AGENT_MEDIA_ID, role: "media", response: "CEO Marcus Webb has not appeared publicly in 72 hours. We have confirmed 47 hospitalizations. The silence is becoming its own story.", sentiment_delta: -0.25, amplification: 0.88 },
    ],
  },
  {
    run_id: RUN_APOLOGY_ID,
    round_number: 2,
    overall_sentiment: -0.42,
    polarization_level: 0.49,
    narrative_state: "CEO Marcus Webb issues a full public apology, takes personal responsibility, announces a $5M compensation fund, and commits to a fully transparent third-party supply chain audit. Public reaction is mixed but the narrative begins to shift.",
    strategy_applied: "apology",
    agent_responses: [
      { agent_id: AGENT_CONSUMER_ID, role: "consumer", response: "Webb finally spoke. The apology felt genuine and the $5M fund is significant. I'm cautious but it's something. Let's see if they follow through.", sentiment_delta: -0.25, amplification: 0.55 },
      { agent_id: AGENT_SUPPORTER_ID, role: "supporter", response: "This is the response I was hoping for. Taking personal responsibility and a real compensation fund — that's how you start to rebuild trust.", sentiment_delta: 0.15, amplification: 0.35 },
      { agent_id: AGENT_CRITIC_ID, role: "critic", response: "The apology was well-executed but I need to see that audit actually happen. And the internal timeline questions haven't been answered yet.", sentiment_delta: -0.18, amplification: 0.52 },
      { agent_id: AGENT_MEDIA_ID, role: "media", response: "The CEO apology and compensation fund announcement is a significant pivot. Markets responded positively. The question is whether the audit reveals more.", sentiment_delta: -0.1, amplification: 0.65 },
    ],
  },
  {
    run_id: RUN_APOLOGY_ID,
    round_number: 3,
    overall_sentiment: -0.28,
    polarization_level: 0.38,
    narrative_state: "Compensation fund enrollment opens. First victims receive direct calls from NutriPlus executives. The class-action lawsuit loses momentum as settlement terms look favorable. Audit firm announced.",
    strategy_applied: null,
    agent_responses: [
      { agent_id: AGENT_CONSUMER_ID, role: "consumer", response: "I got a call from a NutriPlus VP today. They're covering our medical bills and offered fair compensation. I'm still angry but this feels real.", sentiment_delta: 0.12, amplification: 0.42 },
      { agent_id: AGENT_SUPPORTER_ID, role: "supporter", response: "The compensation enrollment is moving fast. They're not fighting it — they're owning it. This is what genuine accountability looks like.", sentiment_delta: 0.35, amplification: 0.38 },
      { agent_id: AGENT_CRITIC_ID, role: "critic", response: "Ernst & Young audit is credible. The compensation fund terms are fair. I'm updating my assessment — this response is better than most I've seen.", sentiment_delta: 0.05, amplification: 0.44 },
      { agent_id: AGENT_MEDIA_ID, role: "media", response: "Crisis communications experts are pointing to NutriPlus's turnaround as a case study in effective apology execution. Retailers reconsidering product pulls.", sentiment_delta: 0.2, amplification: 0.58 },
    ],
  },
  {
    run_id: RUN_APOLOGY_ID,
    round_number: 4,
    overall_sentiment: -0.14,
    polarization_level: 0.28,
    narrative_state: "Audit interim findings show systemic cold-chain improvement plan implemented immediately. 85% of compensation claims resolved. Brand rebuilding narrative begins. Polarization collapses as consensus forms around accountability.",
    strategy_applied: null,
    agent_responses: [
      { agent_id: AGENT_CONSUMER_ID, role: "consumer", response: "My claim was settled fairly and quickly. I still won't buy their products for a while but my anger has cooled. They did what they promised.", sentiment_delta: 0.28, amplification: 0.32 },
      { agent_id: AGENT_SUPPORTER_ID, role: "supporter", response: "The audit interim report is detailed and honest. NutriPlus clearly wants to fix this for real, not just for the headlines.", sentiment_delta: 0.45, amplification: 0.35 },
      { agent_id: AGENT_CRITIC_ID, role: "critic", response: "I'm revising my assessment to cautiously positive. The interim audit findings are self-critical in ways that cost them legally. That's credible.", sentiment_delta: 0.22, amplification: 0.38 },
      { agent_id: AGENT_MEDIA_ID, role: "media", response: "NutriPlus stock has recovered 60% from its trough. The crisis communications turnaround is the business story of the quarter.", sentiment_delta: 0.3, amplification: 0.52 },
    ],
  },
  {
    run_id: RUN_APOLOGY_ID,
    round_number: 5,
    overall_sentiment: -0.05,
    polarization_level: 0.21,
    narrative_state: "Crisis largely contained. Brand NPS returning to pre-crisis levels. Final audit report published. NutriPlus emerges damaged but intact, with a reputation for accountability under pressure.",
    strategy_applied: null,
    agent_responses: [
      { agent_id: AGENT_CONSUMER_ID, role: "consumer", response: "It's been three months. I got fair compensation. The audit was transparent. I still think carefully about their products but the rage is gone.", sentiment_delta: 0.35, amplification: 0.25 },
      { agent_id: AGENT_SUPPORTER_ID, role: "supporter", response: "NutriPlus handled this better than any food company I can remember. I've started buying their products again. Trust rebuilt.", sentiment_delta: 0.55, amplification: 0.28 },
      { agent_id: AGENT_CRITIC_ID, role: "critic", response: "This is what genuine accountability looks like. The full audit is published, supply chain reforms are verified. I'm upgrading my rating.", sentiment_delta: 0.32, amplification: 0.35 },
      { agent_id: AGENT_MEDIA_ID, role: "media", response: "The final chapter: NutriPlus's crisis response is now taught in communications schools as an example of how a company turned catastrophe into credibility.", sentiment_delta: 0.4, amplification: 0.45 },
    ],
  },
];

const clarificationRounds = [
  {
    run_id: RUN_CLARIFICATION_ID,
    round_number: 1,
    overall_sentiment: -0.31,
    polarization_level: 0.42,
    narrative_state: "Initial shock phase identical to baseline. News spreads rapidly. Crisis erupts before any strategy is deployed.",
    strategy_applied: null,
    agent_responses: [
      { agent_id: AGENT_CONSUMER_ID, role: "consumer", response: "My daughter spent two nights in hospital. The company won't pick up the phone. This is unacceptable.", sentiment_delta: -0.45, amplification: 0.78 },
      { agent_id: AGENT_SUPPORTER_ID, role: "supporter", response: "I need to hear from NutriPlus directly before I judge. I hope there's a reasonable explanation.", sentiment_delta: -0.12, amplification: 0.25 },
      { agent_id: AGENT_CRITIC_ID, role: "critic", response: "The recall is mandatory not voluntary. NutriPlus is already managing language. I want the internal lab timeline.", sentiment_delta: -0.38, amplification: 0.72 },
      { agent_id: AGENT_MEDIA_ID, role: "media", response: "47 hospitalizations confirmed. CEO has not appeared. The silence is becoming the story.", sentiment_delta: -0.25, amplification: 0.88 },
    ],
  },
  {
    run_id: RUN_CLARIFICATION_ID,
    round_number: 2,
    overall_sentiment: -0.48,
    polarization_level: 0.55,
    narrative_state: "No strategic response yet. Cold-chain allegation circulates. Class action gains momentum. Sentiment worsens as the information void fills with speculation.",
    strategy_applied: null,
    agent_responses: [
      { agent_id: AGENT_CONSUMER_ID, role: "consumer", response: "Still no compensation offer. Cold-chain excuse is being floated to blame the distributor. Classic deflection.", sentiment_delta: -0.52, amplification: 0.82 },
      { agent_id: AGENT_SUPPORTER_ID, role: "supporter", response: "The cold-chain story is worrying. Waiting to hear the NutriPlus side before I decide what to think.", sentiment_delta: -0.28, amplification: 0.35 },
      { agent_id: AGENT_CRITIC_ID, role: "critic", response: "The distributor scapegoat narrative is emerging. NutriPlus owns final quality control regardless.", sentiment_delta: -0.44, amplification: 0.79 },
      { agent_id: AGENT_MEDIA_ID, role: "media", response: "Shipping records show cold-chain breach timeline is complex. NutriPlus has not clarified their internal detection dates.", sentiment_delta: -0.35, amplification: 0.88 },
    ],
  },
  {
    run_id: RUN_CLARIFICATION_ID,
    round_number: 3,
    overall_sentiment: -0.38,
    polarization_level: 0.46,
    narrative_state: "NutriPlus publishes a detailed public timeline of events, contamination detection, regulatory notifications, and evidence of cold-chain mishandling by NutraChain. The clarity partially reframes the narrative — some skepticism remains.",
    strategy_applied: "clarification",
    agent_responses: [
      { agent_id: AGENT_CONSUMER_ID, role: "consumer", response: "The timeline is detailed and seems credible. The FDA notification was made within 24 hours of their internal lab results. That's not what I expected.", sentiment_delta: -0.18, amplification: 0.52 },
      { agent_id: AGENT_SUPPORTER_ID, role: "supporter", response: "The full timeline actually exonerates NutriPlus on the timeline question. The cold-chain evidence against NutraChain is documented.", sentiment_delta: 0.22, amplification: 0.35 },
      { agent_id: AGENT_CRITIC_ID, role: "critic", response: "The timeline is helpful but I still have questions. Why did it take them 48 hours to release this? And where is the compensation plan?", sentiment_delta: -0.08, amplification: 0.55 },
      { agent_id: AGENT_MEDIA_ID, role: "media", response: "NutriPlus has published a comprehensive timeline with supporting documents. Initial analysis suggests the core contamination cause is the distributor, not manufacturing.", sentiment_delta: 0.05, amplification: 0.62 },
    ],
  },
  {
    run_id: RUN_CLARIFICATION_ID,
    round_number: 4,
    overall_sentiment: -0.27,
    polarization_level: 0.39,
    narrative_state: "FDA validates NutriPlus's internal timeline. Lawsuit shifts focus to NutraChain Distributors. Consumer group remains critical of lack of compensation offer. Partial polarization reduction.",
    strategy_applied: null,
    agent_responses: [
      { agent_id: AGENT_CONSUMER_ID, role: "consumer", response: "The FDA confirmed the timeline. I feel differently about NutriPlus's culpability now. But I still want to know what they're doing for victims.", sentiment_delta: -0.12, amplification: 0.44 },
      { agent_id: AGENT_SUPPORTER_ID, role: "supporter", response: "The facts are becoming clear. NutriPlus did the right thing operationally — the distributor failed on cold chain. The brand deserves a fair hearing.", sentiment_delta: 0.38, amplification: 0.32 },
      { agent_id: AGENT_CRITIC_ID, role: "critic", response: "FDA validation is significant. I'm moderating my position. The remaining concern is victim support — clarification alone doesn't compensate anyone.", sentiment_delta: 0.08, amplification: 0.42 },
      { agent_id: AGENT_MEDIA_ID, role: "media", response: "The story is shifting. NutraChain may face primary liability. NutriPlus stock recovering. Consumer advocates still pushing for financial support.", sentiment_delta: 0.18, amplification: 0.55 },
    ],
  },
  {
    run_id: RUN_CLARIFICATION_ID,
    round_number: 5,
    overall_sentiment: -0.18,
    polarization_level: 0.33,
    narrative_state: "Crisis partially resolved. Facts have been established. NutraChain faces primary liability. NutriPlus recovers partially but the absence of a compensation fund leaves lingering resentment among victims.",
    strategy_applied: null,
    agent_responses: [
      { agent_id: AGENT_CONSUMER_ID, role: "consumer", response: "I accept the factual picture now. The distributor is primarily responsible. But NutriPlus still hasn't compensated victims directly. That still stings.", sentiment_delta: -0.05, amplification: 0.38 },
      { agent_id: AGENT_SUPPORTER_ID, role: "supporter", response: "NutriPlus came through with clarity and honesty. I've resumed buying their products. The transparency earned back my trust.", sentiment_delta: 0.42, amplification: 0.28 },
      { agent_id: AGENT_CRITIC_ID, role: "critic", response: "Clarification worked better than defensiveness. But if they had also compensated victims, this would be a model response. It's a partial win.", sentiment_delta: 0.15, amplification: 0.36 },
      { agent_id: AGENT_MEDIA_ID, role: "media", response: "The NutriPlus clarification strategy succeeded in fact-establishment but not in empathy-building. A compensation component would have closed the loop.", sentiment_delta: 0.22, amplification: 0.42 },
    ],
  },
];

export const demoRoundStates = [...baselineRounds, ...apologyRounds, ...clarificationRounds];

export const demoMetrics = [
  { run_id: RUN_BASELINE_ID, round_number: 1, sentiment_score: -0.31, polarization_score: 0.42, negative_claim_spread: 0.48, stabilization_indicator: 0.12 },
  { run_id: RUN_BASELINE_ID, round_number: 2, sentiment_score: -0.49, polarization_score: 0.56, negative_claim_spread: 0.61, stabilization_indicator: 0.09 },
  { run_id: RUN_BASELINE_ID, round_number: 3, sentiment_score: -0.63, polarization_score: 0.67, negative_claim_spread: 0.74, stabilization_indicator: 0.07 },
  { run_id: RUN_BASELINE_ID, round_number: 4, sentiment_score: -0.74, polarization_score: 0.75, negative_claim_spread: 0.82, stabilization_indicator: 0.05 },
  { run_id: RUN_BASELINE_ID, round_number: 5, sentiment_score: -0.79, polarization_score: 0.81, negative_claim_spread: 0.87, stabilization_indicator: 0.04 },

  { run_id: RUN_APOLOGY_ID, round_number: 1, sentiment_score: -0.31, polarization_score: 0.42, negative_claim_spread: 0.48, stabilization_indicator: 0.12 },
  { run_id: RUN_APOLOGY_ID, round_number: 2, sentiment_score: -0.42, polarization_score: 0.49, negative_claim_spread: 0.52, stabilization_indicator: 0.28 },
  { run_id: RUN_APOLOGY_ID, round_number: 3, sentiment_score: -0.28, polarization_score: 0.38, negative_claim_spread: 0.41, stabilization_indicator: 0.44 },
  { run_id: RUN_APOLOGY_ID, round_number: 4, sentiment_score: -0.14, polarization_score: 0.28, negative_claim_spread: 0.29, stabilization_indicator: 0.62 },
  { run_id: RUN_APOLOGY_ID, round_number: 5, sentiment_score: -0.05, polarization_score: 0.21, negative_claim_spread: 0.18, stabilization_indicator: 0.76 },

  { run_id: RUN_CLARIFICATION_ID, round_number: 1, sentiment_score: -0.31, polarization_score: 0.42, negative_claim_spread: 0.48, stabilization_indicator: 0.12 },
  { run_id: RUN_CLARIFICATION_ID, round_number: 2, sentiment_score: -0.48, polarization_score: 0.55, negative_claim_spread: 0.60, stabilization_indicator: 0.10 },
  { run_id: RUN_CLARIFICATION_ID, round_number: 3, sentiment_score: -0.38, polarization_score: 0.46, negative_claim_spread: 0.49, stabilization_indicator: 0.31 },
  { run_id: RUN_CLARIFICATION_ID, round_number: 4, sentiment_score: -0.27, polarization_score: 0.39, negative_claim_spread: 0.38, stabilization_indicator: 0.43 },
  { run_id: RUN_CLARIFICATION_ID, round_number: 5, sentiment_score: -0.18, polarization_score: 0.33, negative_claim_spread: 0.31, stabilization_indicator: 0.52 },
];
