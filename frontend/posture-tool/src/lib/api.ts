export async function analyzePosture(
  file: File
) {

  const formData = new FormData()

  formData.append(
    "side_image",
    file
  )

  const response = await fetch(
    "http://127.0.0.1:8000/posture/analyze",
    {
      method: "POST",
      body: formData
    }
  )

  if (!response.ok) {
    throw new Error(
      "Failed to analyze posture"
    )
  }

  return response.json()
}