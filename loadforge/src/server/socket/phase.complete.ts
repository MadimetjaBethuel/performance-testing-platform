import { subscribe } from "./eventbus";
import { db } from "../db/index";
import { testPhases } from "../db/schema";
export const onPhaseComplete = () => {
    return subscribe(async(event) => {
        if (event.type != "phase_complete") return;
        
    const phaseData = event.data;
        console.log("💾 [DB] Phase complete event received:", phaseData);

    await db.insert(testPhases).values({
        id: "123456577wedwxdfvdvd", 
        user_id: "phaseData.user_id",
        phase_number: phaseData.phase,
        total_phases: phaseData.total_phases,
        concurrency: phaseData.concurrency,
        success_count: phaseData.success_count,
        error_count: phaseData.error_count,
        percentile: phaseData.percentiles,
        requests: phaseData.requests,
    })
})}