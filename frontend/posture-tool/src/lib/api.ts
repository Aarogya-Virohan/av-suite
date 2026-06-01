import type { PostureReport } from "@/types/posture"

interface AnalyzePosturePayload {
frontFile: File
sideFile: File
backFile: File

patientName: string
age: string
gender: string
caseRef: string
}

export async function analyzePosture(
payload: AnalyzePosturePayload,
): Promise<PostureReport> {

const formData = new FormData()

formData.append(
"front_image",
payload.frontFile,
)

formData.append(
"side_image",
payload.sideFile,
)

formData.append(
"back_image",
payload.backFile,
)

formData.append(
"patient_name",
payload.patientName,
)

formData.append(
"age",
payload.age,
)

formData.append(
"gender",
payload.gender,
)

formData.append(
"case_ref",
payload.caseRef,
)

const response = await fetch(
"http://127.0.0.1:8000/posture/analyze",
{
method: "POST",
body: formData,
},
)

if (!response.ok) {
throw new Error(
"Failed to analyze posture",
)
}

return response.json()
}
