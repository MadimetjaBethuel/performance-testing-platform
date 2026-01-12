import { subscribe } from "./eventbus";
import { db } from "../db/index";
import { testPhases } from "../db/schema";
import { v4 as uuidv4 } from "uuid";
import { eq, and } from "drizzle-orm";

const DEFAULT_USER_ID = "default-user-001";
const processedPhases = new Set<string>();
export const onPhaseComplete = () => {
  return subscribe(async (event) => {
    if (event.type !== "phase_complete") return;

    const phaseData = event.data;

    const phaseKey = `${phaseData.test_id}-${phaseData.phase}`;

    if (processedPhases.has(phaseKey)) {
      return;
    }

    try {
      const existingPhase = await db
        .select()
        .from(testPhases)
        .where(
          and(
            eq(testPhases.test_id, phaseData.test_id),
            eq(testPhases.phase_number, phaseData.phase)
          )
        )
        .limit(1);

      if (existingPhase.length > 0) {
        console.log(
          `⏭️ [DB] Phase ${phaseData.phase} for test ${phaseData.test_id} already exists in database`
        );
        // Add to cache to prevent future checks
        processedPhases.add(phaseKey);
        return;
      }
      const phase_id = uuidv4();

      await db.insert(testPhases).values({
        id: phase_id,
        test_id: phaseData.test_id,
        user_id: DEFAULT_USER_ID,
        phase_number: phaseData.phase,
        total_phases: phaseData.total_phases,
        concurrency: phaseData.concurrency,
        success_count: phaseData.success_count,
        error_count: phaseData.error_count,
        percentile: phaseData.percentiles,
        requests: phaseData.requests,
      });

      processedPhases.add(phaseKey);

      if (processedPhases.size > 100) {
        processedPhases.clear();
      }
    } catch (error: any) {
      console.error("❌ [DB] Failed to save phase data:", error);
      if (error?.code === "23505") {
        console.log(
          `⏭️ [DB] Phase ${phaseData.phase} for test ${phaseData.test_id} already exists (unique constraint)`
        );
        processedPhases.add(phaseKey);
        return;
      }
      console.error("❌ [DB] Failed to save phase data:", error);
      console.error("Error details:", {
        message: error?.message,
        code: error?.code,
        constraint: error?.constraint,
      });
    }
  });
};
