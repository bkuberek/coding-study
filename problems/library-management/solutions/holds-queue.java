import java.util.*;

public class Library {
    private record FinePolicy(long perDay) {
        long fine(long due, long returned) {
            return Math.max(0, returned - due) * perDay;
        }
    }

    /** All copies of one ISBN, with the members waiting for one. */
    private static final class Title {
        int copies;
        int onLoan;
        final Set<String> reserved = new HashSet<>(); // members with a copy set aside for them
        final Deque<String> waiting = new ArrayDeque<>();

        int free() {
            return copies - onLoan - reserved.size();
        }

        /** Invariant: a free copy never sits on the shelf while someone is waiting. */
        void assignFreeCopies() {
            while (free() > 0 && !waiting.isEmpty()) {
                reserved.add(waiting.pollFirst());
            }
        }
    }

    private static final class Member {
        final int maxLoans;
        final Map<String, Long> loans = new HashMap<>(); // isbn -> due day
        long fines;

        Member(int maxLoans) {
            this.maxLoans = maxLoans;
        }

        boolean canBorrow(String isbn) {
            return fines == 0 && !loans.containsKey(isbn) && loans.size() < maxLoans;
        }
    }

    private final int loanDays;
    private final FinePolicy finePolicy;
    private final Map<String, Title> titles = new HashMap<>();
    private final Map<String, Member> members = new HashMap<>();

    public Library(int loanDays, int finePerDay) {
        this.loanDays = loanDays;
        this.finePolicy = new FinePolicy(finePerDay);
    }

    public int addBook(String isbn, int copies) {
        Title title = titles.computeIfAbsent(isbn, key -> new Title());
        title.copies += copies;
        title.assignFreeCopies();
        return title.copies;
    }

    public boolean addMember(String memberId, int maxLoans) {
        return members.putIfAbsent(memberId, new Member(maxLoans)) == null;
    }

    public long checkout(long day, String memberId, String isbn) {
        Member member = members.get(memberId);
        Title title = titles.get(isbn);
        if (member == null || title == null || !member.canBorrow(isbn)) {
            return -1;
        }
        if (!title.reserved.remove(memberId) && title.free() == 0) {
            return -1;
        }
        title.onLoan++;
        long due = day + loanDays;
        member.loans.put(isbn, due);
        return due;
    }

    public long returnBook(long day, String memberId, String isbn) {
        Member member = members.get(memberId);
        if (member == null || !member.loans.containsKey(isbn)) {
            return -1;
        }
        long fine = finePolicy.fine(member.loans.remove(isbn), day);
        member.fines += fine;
        Title title = titles.get(isbn);
        title.onLoan--;
        title.assignFreeCopies();
        return fine;
    }

    public int placeHold(long day, String memberId, String isbn) {
        Member member = members.get(memberId);
        Title title = titles.get(isbn);
        if (member == null || title == null || title.free() > 0) {
            return -1;
        }
        if (member.loans.containsKey(isbn) || title.reserved.contains(memberId) || title.waiting.contains(memberId)) {
            return -1;
        }
        title.waiting.addLast(memberId);
        return title.waiting.size();
    }

    public boolean cancelHold(long day, String memberId, String isbn) {
        Title title = titles.get(isbn);
        if (title == null) {
            return false;
        }
        if (title.waiting.remove(memberId)) {
            return true;
        }
        if (title.reserved.remove(memberId)) {
            title.assignFreeCopies();
            return true;
        }
        return false;
    }

    public long renew(long day, String memberId, String isbn) {
        Member member = members.get(memberId);
        if (member == null || !member.loans.containsKey(isbn)) {
            return -1;
        }
        long due = member.loans.get(isbn);
        if (day > due || !titles.get(isbn).waiting.isEmpty()) {
            return -1;
        }
        member.loans.put(isbn, due + loanDays);
        return due + loanDays;
    }

    public long fines(long day, String memberId) {
        Member member = members.get(memberId);
        return member == null ? -1 : member.fines;
    }

    public long payFine(long day, String memberId, long amount) {
        Member member = members.get(memberId);
        if (member == null) {
            return -1;
        }
        member.fines = Math.max(0, member.fines - amount);
        return member.fines;
    }

    public int available(long day, String isbn) {
        Title title = titles.get(isbn);
        return title == null ? -1 : title.free();
    }
}
