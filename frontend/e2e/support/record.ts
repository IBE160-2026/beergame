/** A Studentside record (Story 13.2) for a mocked `/record` route: an Assistant lecturer's view of
 * a Student with nothing done yet, carrying the given «KI-vurdering» (Story 12.5). */
export function staffRecord(ids: { session: string; classId: string; student: string }, assessment: unknown) {
  return {
    class_session_id: ids.session,
    class_id: ids.classId,
    class_name: "Logistikk 1",
    session_number: 1,
    user_id: ids.student,
    name: "Sara Student",
    can_manage: false,
    can_correct: false,
    can_give_makeup: false,
    test_deadline: null,
    completion: null,
    participation: null,
    game: null,
    makeup: null,
    debrief: { explanation: null, explanation_saved_at: null, finished_at: null, late: false, moments: 0 },
    quiz: [],
    replay: null,
    test: null,
    assessment,
    report: null,
  };
}
