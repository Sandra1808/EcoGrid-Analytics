package EcoGrid.Backend.entity;

import jakarta.persistence.*;
import jakarta.validation.constraints.NotNull;
import org.hibernate.annotations.OnDelete;
import org.hibernate.annotations.OnDeleteAction;

import java.math.BigDecimal;

@Entity
@Table(name = "REDTRANSPORTE")
public class Redtransporte {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "IDRED", nullable = false)
    private Long id;

    @NotNull
    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @OnDelete(action = OnDeleteAction.RESTRICT)
    @JoinColumn(name = "IDCCAA", nullable = false)
    private Comunidadautonoma idccaa;

    @NotNull
    @Column(name = "YEAR", nullable = false)
    private Short year;

    @Column(name = "KMLINEAS400KV", precision = 10, scale = 2)
    private BigDecimal kmlineas400kv;

    @Column(name = "KMLINEAS220KV", precision = 10, scale = 2)
    private BigDecimal kmlineas220kv;

    @Column(name = "NUMPOSICIONES")
    private Long numposiciones;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public Comunidadautonoma getIdccaa() {
        return idccaa;
    }

    public void setIdccaa(Comunidadautonoma idccaa) {
        this.idccaa = idccaa;
    }

    public Short getYear() {
        return year;
    }

    public void setYear(Short year) {
        this.year = year;
    }

    public BigDecimal getKmlineas400kv() {
        return kmlineas400kv;
    }

    public void setKmlineas400kv(BigDecimal kmlineas400kv) {
        this.kmlineas400kv = kmlineas400kv;
    }

    public BigDecimal getKmlineas220kv() {
        return kmlineas220kv;
    }

    public void setKmlineas220kv(BigDecimal kmlineas220kv) {
        this.kmlineas220kv = kmlineas220kv;
    }

    public Long getNumposiciones() {
        return numposiciones;
    }

    public void setNumposiciones(Long numposiciones) {
        this.numposiciones = numposiciones;
    }

}