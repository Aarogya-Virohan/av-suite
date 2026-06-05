with open("backend/app/api/v1/exercises.py", "r") as f:
    content = f.read()

# remove the block from the end
block_to_move = """
@router.get(
    "/by-condition",
    response_model=ResponseEnvelope[List[ExerciseRead]],
    tags=["Exercises"]
)
async def get_exercises_by_condition(
    request: Request,
    condition: str = Query(..., description="Medical condition (e.g., shoulder_pain)"),
    db: AsyncSession = Depends(get_db)
):
    \"\"\"
    Endpoint ka purpose: Condition ke base par exercises recommend karna
    CDSS hook for intelligent exercise recommendations.
    \"\"\"
    logger.info(f"Get exercises by condition request - condition: {condition}")
    
    try:
        clinic_id = request.state.clinic_id
        
        exercises = await exercise_service.get_exercises_by_condition(db, clinic_id, condition)
        
        return ResponseEnvelope(data=exercises)
        
    except Exception as e:
        logger.error(f"Get exercises by condition error: {str(e)}")
        raise
"""
if block_to_move in content:
    content = content.replace(block_to_move, "")
    
    # insert before get_exercise
    target = "@router.get(\n    \"/{id}\","
    content = content.replace(target, block_to_move + "\n\n" + target)
    
    with open("backend/app/api/v1/exercises.py", "w") as f:
        f.write(content)
    print("Fixed!")
else:
    print("Block not found")
