ALTER TABLE "loadforge_load_test" DROP CONSTRAINT "loadforge_load_test_test_phase_id_loadforge_test_phase_id_fk";
--> statement-breakpoint
ALTER TABLE "loadforge_test_phase" ADD COLUMN "test_id" varchar;--> statement-breakpoint
ALTER TABLE "loadforge_test_phase" ADD CONSTRAINT "loadforge_test_phase_test_id_loadforge_load_test_id_fk" FOREIGN KEY ("test_id") REFERENCES "public"."loadforge_load_test"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "loadforge_load_test" DROP COLUMN "test_phase_id";